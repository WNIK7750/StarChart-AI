from collections.abc import Callable
from contextlib import contextmanager
from functools import lru_cache
from sqlite3 import Connection
from time import time
from typing import Iterator

from app.core.security import hash_token
from app.db.database import get_connection
from app.users.common import UsersError


AUTH_RATE_LIMIT_RULES = {
    "username_available": (("ip", 30, 60),),
    "register": (("ip", 5, 300),),
    "login": (("ip", 20, 60), ("identifier", 10, 300)),
    "password_reset_start": (("ip", 10, 300), ("identifier", 5, 300)),
    "password_reset_verify": (("ip", 20, 300), ("challenge", 10, 300)),
    "password_reset_confirm": (("ip", 10, 300), ("token", 5, 300)),
    "refresh": (("ip", 30, 60),),
}


class SQLiteAuthRateLimitRepository:
    def __init__(self, connection_factory: Callable[[], Connection] = get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        conn = self._connection_factory()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def consume(self, scope: str, subject_hash: str, limit: int, window_seconds: int, now: int) -> dict:
        window_key = now // window_seconds
        expires_at = (window_key + 1) * window_seconds
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM user_auth_rate_limits WHERE expires_at < ?", (now,))
            conn.execute(
                """
                INSERT INTO user_auth_rate_limits(scope, subject_hash, window_key, request_count, expires_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(scope, subject_hash) DO UPDATE SET
                  window_key = excluded.window_key,
                  request_count = CASE
                    WHEN user_auth_rate_limits.window_key = excluded.window_key
                    THEN user_auth_rate_limits.request_count + 1
                    ELSE 1
                  END,
                  expires_at = excluded.expires_at,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (scope, subject_hash, window_key, expires_at),
            )
            row = conn.execute(
                "SELECT request_count FROM user_auth_rate_limits WHERE scope = ? AND subject_hash = ?",
                (scope, subject_hash),
            ).fetchone()
        count = int(row["request_count"] if isinstance(row, dict) else row[0])
        return {
            "allowed": count <= limit,
            "limit": limit,
            "remaining": max(0, limit - count),
            "retryAfter": max(1, expires_at - now),
        }


class AuthRateLimiter:
    def __init__(self, repository: SQLiteAuthRateLimitRepository, clock: Callable[[], float] = time):
        self.repository = repository
        self.clock = clock

    def enforce(self, operation: str, subjects: dict[str, str]) -> None:
        rules = AUTH_RATE_LIMIT_RULES[operation]
        now = int(self.clock())
        retry_after = 0
        for subject_type, limit, window_seconds in rules:
            value = subjects.get(subject_type, "").strip().lower()
            if not value:
                continue
            result = self.repository.consume(
                f"{operation}:{subject_type}",
                hash_token(f"auth-rate-limit:{operation}:{subject_type}:{value}"),
                limit,
                window_seconds,
                now,
            )
            if not result["allowed"]:
                retry_after = max(retry_after, result["retryAfter"])
        if retry_after:
            error = UsersError("AUTH_RATE_LIMITED", "请求过于频繁，请稍后重试", 429)
            error.retry_after = retry_after
            raise error


@lru_cache(maxsize=1)
def get_auth_rate_limiter() -> AuthRateLimiter:
    return AuthRateLimiter(SQLiteAuthRateLimitRepository())
