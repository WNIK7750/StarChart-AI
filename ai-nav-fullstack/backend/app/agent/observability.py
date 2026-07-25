from collections import Counter, deque
from dataclasses import dataclass
from hashlib import sha256
from math import ceil
import re
from threading import Lock
from time import time
from typing import Callable


SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
TRACE_TOOL_ALLOWLIST = {
    "learning.search",
    "tools.search",
    "tools.workflow",
    "users.context",
    "navigation.read",
}
VALIDATION_FALLBACKS = {"invalid_output", "sensitive_input"}
TRACE_FIELDS = {
    "requestId",
    "mode",
    "provider",
    "model",
    "attempts",
    "fallbackReason",
    "validationError",
    "promptVersion",
    "evidenceCount",
    "tools",
    "latencyMs",
    "inputTokens",
    "outputTokens",
    "costCny",
}


def build_agent_trace(
    *,
    request_id: str,
    mode: str,
    provider: str | None,
    model: str | None,
    attempts: int,
    fallback_reason: str | None,
    prompt_version: str,
    evidence_count: int,
    tools: tuple[str, ...],
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    cost_cny: float | None,
) -> dict:
    safe_reason = (
        fallback_reason
        if fallback_reason and SAFE_LABEL.fullmatch(fallback_reason)
        else None
    )
    safe_tools = sorted(
        {
            tool
            for tool in tools
            if isinstance(tool, str) and tool in TRACE_TOOL_ALLOWLIST
        }
    )
    safe_attempts = attempts if isinstance(attempts, int) and not isinstance(attempts, bool) else 0
    safe_evidence_count = (
        evidence_count
        if isinstance(evidence_count, int) and not isinstance(evidence_count, bool)
        else 0
    )
    trace = {
        "requestId": sha256(
            request_id.encode("utf-8")
            if isinstance(request_id, str)
            else b"invalid"
        ).hexdigest()[:24],
        "mode": mode if mode in {"deterministic", "provider"} else "unknown",
        "provider": (
            provider if provider and SAFE_LABEL.fullmatch(provider) else None
        ),
        "model": model if model and SAFE_LABEL.fullmatch(model) else None,
        "attempts": max(0, min(safe_attempts, 2)),
        "fallbackReason": safe_reason,
        "validationError": (
            safe_reason if safe_reason in VALIDATION_FALLBACKS else None
        ),
        "promptVersion": (
            prompt_version
            if prompt_version and SAFE_LABEL.fullmatch(prompt_version)
            else "unknown"
        ),
        "evidenceCount": max(0, min(safe_evidence_count, 100)),
        "tools": safe_tools,
        "latencyMs": max(0.0, round(float(latency_ms), 2)),
        "inputTokens": max(0, int(input_tokens)),
        "outputTokens": max(0, int(output_tokens)),
        "costCny": round(max(0.0, float(cost_cny)), 8) if cost_cny is not None else None,
    }
    if set(trace) != TRACE_FIELDS:
        raise RuntimeError("Agent trace fields drifted from the allowlist")
    return trace


@dataclass(frozen=True, slots=True)
class AgentOperationEvent:
    timestamp: float
    mode: str
    provider: str
    model: str
    fallback_reason: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_cny: float


class AgentMetrics:
    """Bounded process-local Agent metrics without user or content labels."""

    WINDOW_SECONDS = 300
    MAX_RECENT_EVENTS = 5000
    MAX_MODEL_LABELS = 16

    def __init__(self, *, clock: Callable[[], float] = time) -> None:
        self._clock = clock
        self._lock = Lock()
        self._events: deque[AgentOperationEvent] = deque(
            maxlen=self.MAX_RECENT_EVENTS
        )
        self._outcomes: Counter[tuple[str, str]] = Counter()
        self._model_totals: Counter[tuple[str, str]] = Counter()
        self._replay_hits = 0
        self._request_id_conflicts = 0

    @staticmethod
    def _label(value: str | None) -> str:
        return value if value and SAFE_LABEL.fullmatch(value) else "none"

    def _model_key(self, provider: str, model: str) -> tuple[str, str]:
        key = (provider, model)
        if key in self._model_totals or len(self._model_totals) < self.MAX_MODEL_LABELS:
            return key
        return ("other", "other")

    def record(
        self,
        *,
        mode: str,
        provider: str | None,
        model: str | None,
        fallback_reason: str | None,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        cost_cny: float | None,
    ) -> None:
        safe_mode = mode if mode in {"deterministic", "provider"} else "unknown"
        safe_provider = self._label(provider)
        safe_model = self._label(model)
        safe_reason = self._label(fallback_reason)
        event = AgentOperationEvent(
            timestamp=self._clock(),
            mode=safe_mode,
            provider=safe_provider,
            model=safe_model,
            fallback_reason=safe_reason,
            latency_ms=max(0.0, float(latency_ms)),
            input_tokens=max(0, int(input_tokens)),
            output_tokens=max(0, int(output_tokens)),
            cost_cny=max(0.0, float(cost_cny or 0)),
        )
        outcome = (
            "provider_success"
            if safe_mode == "provider"
            else "fallback"
            if safe_reason != "none"
            else "deterministic"
        )
        with self._lock:
            self._events.append(event)
            self._outcomes[(outcome, safe_reason)] += 1
            self._model_totals[self._model_key(safe_provider, safe_model)] += 1

    def record_replay_hit(self) -> None:
        with self._lock:
            self._replay_hits += 1

    def record_request_id_conflict(self) -> None:
        with self._lock:
            self._request_id_conflicts += 1

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = max(0, ceil(len(ordered) * percentile) - 1)
        return round(ordered[index], 2)

    @staticmethod
    def _alerts(events: list[AgentOperationEvent]) -> list[dict]:
        alerts: list[dict] = []
        total = len(events)
        fallbacks = sum(1 for event in events if event.fallback_reason != "none")
        if total >= 10 and fallbacks / total >= 0.2:
            alerts.append(
                {
                    "code": "AGENT_PROVIDER_FALLBACK_RATE_HIGH",
                    "count": fallbacks,
                    "threshold": 0.2,
                }
            )
        invalid_outputs = sum(
            1 for event in events if event.fallback_reason == "invalid_output"
        )
        if invalid_outputs:
            alerts.append(
                {
                    "code": "AGENT_PROVIDER_INVALID_OUTPUT",
                    "count": invalid_outputs,
                    "threshold": 1,
                }
            )
        budget_rejections = sum(
            1 for event in events if event.fallback_reason == "budget_exceeded"
        )
        if budget_rejections >= 3:
            alerts.append(
                {
                    "code": "AGENT_BUDGET_REJECTIONS_HIGH",
                    "count": budget_rejections,
                    "threshold": 3,
                }
            )
        if len(events) >= 5:
            p95 = AgentMetrics._percentile(
                [event.latency_ms for event in events],
                0.95,
            )
            if p95 >= 5000:
                alerts.append(
                    {
                        "code": "AGENT_LATENCY_P95_HIGH",
                        "value": p95,
                        "threshold": 5000,
                    }
                )
        return alerts

    def snapshot(self) -> dict:
        now = self._clock()
        cutoff = now - self.WINDOW_SECONDS
        with self._lock:
            recent = [event for event in self._events if event.timestamp >= cutoff]
            outcomes = [
                {
                    "outcome": outcome,
                    "fallbackReason": reason,
                    "count": count,
                }
                for (outcome, reason), count in sorted(self._outcomes.items())
            ]
            models = [
                {"provider": provider, "model": model, "count": count}
                for (provider, model), count in sorted(self._model_totals.items())
            ]
            replay_hits = self._replay_hits
            request_id_conflicts = self._request_id_conflicts

        latencies = [event.latency_ms for event in recent]
        return {
            "windowSeconds": self.WINDOW_SECONDS,
            "recent": {
                "requestCount": len(recent),
                "providerSuccessCount": sum(
                    1 for event in recent if event.mode == "provider"
                ),
                "fallbackCount": sum(
                    1 for event in recent if event.fallback_reason != "none"
                ),
                "inputTokens": sum(event.input_tokens for event in recent),
                "outputTokens": sum(event.output_tokens for event in recent),
                "costCny": round(sum(event.cost_cny for event in recent), 8),
                "latencyP50Ms": self._percentile(latencies, 0.5),
                "latencyP95Ms": self._percentile(latencies, 0.95),
            },
            "counters": {
                "outcomes": outcomes,
                "models": models,
                "replayHits": replay_hits,
                "requestIdConflicts": request_id_conflicts,
            },
            "alerts": self._alerts(recent),
            "meta": {
                "source": "agent.observability",
                "containsPii": False,
                "containsContent": False,
                "processLocal": True,
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._outcomes.clear()
            self._model_totals.clear()
            self._replay_hits = 0
            self._request_id_conflicts = 0


_METRICS = AgentMetrics()


def get_agent_metrics() -> AgentMetrics:
    return _METRICS
