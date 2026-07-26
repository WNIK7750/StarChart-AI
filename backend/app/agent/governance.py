import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from threading import Lock
from time import monotonic
from typing import Callable

from app.agent.providers import ProviderRequest, ProviderResult


CN_TIMEZONE = timezone(timedelta(hours=8), "Asia/Shanghai")


class AgentGovernanceRejected(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class AgentAdmissionGate:
    """Process-local concurrency gate shared by all Agent orchestrators."""

    def __init__(
        self,
        *,
        per_user_limit: int,
        global_limit: int,
        queue_limit: int,
        queue_timeout_seconds: float,
        clock: Callable[[], float] = monotonic,
    ):
        self.per_user_limit = per_user_limit
        self.global_limit = global_limit
        self.queue_limit = queue_limit
        self.queue_timeout_seconds = queue_timeout_seconds
        self._clock = clock
        self._lock = Lock()
        self._global_inflight = 0
        self._per_user_inflight: dict[str, int] = {}
        self._waiting = 0

    @asynccontextmanager
    async def slot(self, user_key: str):
        acquired = False
        waiting = False
        deadline = self._clock() + self.queue_timeout_seconds
        try:
            while not acquired:
                with self._lock:
                    user_inflight = self._per_user_inflight.get(user_key, 0)
                    if (
                        self._global_inflight < self.global_limit
                        and user_inflight < self.per_user_limit
                    ):
                        self._global_inflight += 1
                        self._per_user_inflight[user_key] = user_inflight + 1
                        acquired = True
                        if waiting:
                            self._waiting -= 1
                            waiting = False
                    elif not waiting:
                        if self._waiting >= self.queue_limit:
                            raise AgentGovernanceRejected("capacity_limited")
                        self._waiting += 1
                        waiting = True

                if acquired:
                    break
                remaining = deadline - self._clock()
                if remaining <= 0:
                    raise AgentGovernanceRejected("capacity_limited")
                await asyncio.sleep(min(0.01, remaining))
            yield
        finally:
            with self._lock:
                if waiting:
                    self._waiting -= 1
                if acquired:
                    self._global_inflight -= 1
                    next_count = self._per_user_inflight.get(user_key, 1) - 1
                    if next_count <= 0:
                        self._per_user_inflight.pop(user_key, None)
                    else:
                        self._per_user_inflight[user_key] = next_count


@dataclass(slots=True)
class AgentBudgetReservation:
    guard: "AgentCostGuard"
    user_key: str
    day_key: str
    month_key: str
    estimated_cny: float
    settled: bool = False

    def settle(self, result: ProviderResult | None) -> float:
        if self.settled:
            return self.estimated_cny
        actual_cny = self.guard.result_cost(result) if result is not None else None
        charged_cny = self.estimated_cny if actual_cny is None else actual_cny
        self.guard._settle(self, charged_cny)
        self.settled = True
        return charged_cny


class AgentCostGuard:
    """Process-local conservative cost ledger; provider balance remains the final hard cap."""

    def __init__(
        self,
        *,
        max_input_tokens: int,
        max_output_tokens: int,
        input_cny_per_million: float,
        output_cny_per_million: float,
        per_request_cost_cny: float,
        per_user_daily_cost_cny: float,
        global_daily_cost_cny: float,
        global_monthly_cost_cny: float,
        now: Callable[[], datetime] | None = None,
    ):
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.input_cny_per_million = input_cny_per_million
        self.output_cny_per_million = output_cny_per_million
        self.per_request_cost_cny = per_request_cost_cny
        self.per_user_daily_cost_cny = per_user_daily_cost_cny
        self.global_daily_cost_cny = global_daily_cost_cny
        self.global_monthly_cost_cny = global_monthly_cost_cny
        self._now = now or (lambda: datetime.now(CN_TIMEZONE))
        self._lock = Lock()
        self._user_daily: dict[tuple[str, str], float] = {}
        self._global_daily: dict[str, float] = {}
        self._global_monthly: dict[str, float] = {}
        self._current_day: str | None = None
        self._current_month: str | None = None

    @staticmethod
    def estimate_tokens(value: str) -> int:
        if not value:
            return 0
        return max(len(value), ceil(len(value.encode("utf-8")) / 4))

    def estimate_request(self, request: ProviderRequest) -> tuple[int, float]:
        input_text = "\n".join(
            (
                request.system_instruction,
                *(message.content for message in request.history),
                request.user_message,
                *(
                    "\n".join(
                        (
                            item.citation_id,
                            item.source_type,
                            item.source_key,
                            item.title,
                            item.summary,
                            item.href,
                        )
                    )
                    for item in request.evidence
                ),
            )
        )
        input_tokens = self.estimate_tokens(input_text) + 256
        estimated_cny = (
            input_tokens * self.input_cny_per_million
            + self.max_output_tokens * self.output_cny_per_million
        ) / 1_000_000
        return input_tokens, estimated_cny

    def reserve(self, user_key: str, request: ProviderRequest) -> AgentBudgetReservation:
        input_tokens, estimated_cny = self.estimate_request(request)
        if input_tokens > self.max_input_tokens or estimated_cny > self.per_request_cost_cny:
            raise AgentGovernanceRejected("budget_exceeded")

        now = self._now().astimezone(CN_TIMEZONE)
        day_key = now.date().isoformat()
        month_key = day_key[:7]
        with self._lock:
            if self._current_day != day_key:
                self._user_daily.clear()
                self._global_daily.clear()
                self._current_day = day_key
            if self._current_month != month_key:
                self._global_monthly.clear()
                self._current_month = month_key
            user_total = self._user_daily.get((user_key, day_key), 0.0)
            day_total = self._global_daily.get(day_key, 0.0)
            month_total = self._global_monthly.get(month_key, 0.0)
            if (
                user_total + estimated_cny > self.per_user_daily_cost_cny
                or day_total + estimated_cny > self.global_daily_cost_cny
                or month_total + estimated_cny > self.global_monthly_cost_cny
            ):
                raise AgentGovernanceRejected("budget_exceeded")
            self._user_daily[(user_key, day_key)] = user_total + estimated_cny
            self._global_daily[day_key] = day_total + estimated_cny
            self._global_monthly[month_key] = month_total + estimated_cny
        return AgentBudgetReservation(self, user_key, day_key, month_key, estimated_cny)

    def result_cost(self, result: ProviderResult) -> float | None:
        if not self._has_valid_usage(result):
            return None
        if result.input_tokens <= 0 and result.output_tokens <= 0:
            return None
        return (
            result.input_tokens * self.input_cny_per_million
            + result.output_tokens * self.output_cny_per_million
        ) / 1_000_000

    def result_exceeds_request_limit(
        self,
        result: ProviderResult,
        charged_cny: float,
    ) -> bool:
        if not self._has_valid_usage(result):
            return False
        return (
            result.input_tokens > self.max_input_tokens
            or result.output_tokens > self.max_output_tokens
            or charged_cny > self.per_request_cost_cny
        )

    @staticmethod
    def _has_valid_usage(result: ProviderResult) -> bool:
        return (
            isinstance(result.input_tokens, int)
            and not isinstance(result.input_tokens, bool)
            and result.input_tokens >= 0
            and isinstance(result.output_tokens, int)
            and not isinstance(result.output_tokens, bool)
            and result.output_tokens >= 0
        )

    def _settle(self, reservation: AgentBudgetReservation, charged_cny: float) -> None:
        delta = charged_cny - reservation.estimated_cny
        with self._lock:
            if reservation.day_key == self._current_day:
                user_key = (reservation.user_key, reservation.day_key)
                self._user_daily[user_key] = max(
                    0.0,
                    self._user_daily.get(user_key, 0.0) + delta,
                )
                self._global_daily[reservation.day_key] = max(
                    0.0,
                    self._global_daily.get(reservation.day_key, 0.0) + delta,
                )
            if reservation.month_key == self._current_month:
                self._global_monthly[reservation.month_key] = max(
                    0.0,
                    self._global_monthly.get(reservation.month_key, 0.0) + delta,
                )


@dataclass(frozen=True, slots=True)
class AgentRuntimeGovernance:
    admission: AgentAdmissionGate
    cost: AgentCostGuard
