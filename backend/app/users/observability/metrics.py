from collections import Counter, deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass(frozen=True)
class OperationEvent:
    timestamp: float
    operation: str
    status_code: int
    error_code: str | None


class UsersMetrics:
    WINDOW_SECONDS = 300

    def __init__(self) -> None:
        self._lock = Lock()
        self._counts: Counter[tuple[str, str, str]] = Counter()
        self._events: deque[OperationEvent] = deque()

    def record(self, operation: str, status_code: int, error_code: str | None) -> None:
        outcome = "success" if status_code < 400 else "error"
        code = error_code or "NONE"
        now = time()
        with self._lock:
            self._counts[(operation, outcome, code)] += 1
            self._events.append(OperationEvent(now, operation, status_code, error_code))
            self._discard_expired(now)

    def _discard_expired(self, now: float) -> None:
        cutoff = now - self.WINDOW_SECONDS
        while self._events and self._events[0].timestamp < cutoff:
            self._events.popleft()

    def snapshot(self) -> dict:
        now = time()
        with self._lock:
            self._discard_expired(now)
            counters = [
                {"operation": operation, "outcome": outcome, "errorCode": code, "count": count}
                for (operation, outcome, code), count in sorted(self._counts.items())
            ]
            recent = list(self._events)
        return {
            "windowSeconds": self.WINDOW_SECONDS,
            "counters": counters,
            "alerts": self._alerts(recent),
            "meta": {"source": "users.observability", "containsPii": False},
        }

    @staticmethod
    def _alerts(events: list[OperationEvent]) -> list[dict]:
        rules = (
            ("auth.login", 401, 5, "AUTH_LOGIN_FAILURE_SPIKE"),
            ("auth.login", 423, 1, "AUTH_ACCOUNT_LOCKED"),
            ("auth.refresh", 400, 3, "AUTH_REFRESH_FAILURE_SPIKE"),
            ("users.password.update", 400, 3, "PASSWORD_UPDATE_FAILURE_SPIKE"),
            ("users.session.revoke", 400, 3, "SESSION_REVOKE_FAILURE_SPIKE"),
        )
        alerts = []
        for operation, minimum_status, threshold, code in rules:
            count = sum(
                1
                for event in events
                if event.operation == operation and event.status_code >= minimum_status
            )
            if count >= threshold:
                alerts.append({"code": code, "operation": operation, "count": count, "threshold": threshold})
        return alerts

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()
            self._events.clear()


_METRICS = UsersMetrics()


def get_users_metrics() -> UsersMetrics:
    return _METRICS
