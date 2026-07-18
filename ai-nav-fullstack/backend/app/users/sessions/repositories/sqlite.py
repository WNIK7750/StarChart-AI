from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteSessionsRepository:
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

    def list_sessions(self, user_id: int, limit: int, offset: int, current_refresh_token_hash: str | None = None) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_uid AS sessionUid, device_name AS deviceName, user_agent AS userAgent,
                       ip_address AS ipAddress, is_revoked AS isRevoked, expires_at AS expiresAt,
                       last_seen_at AS lastSeenAt, created_at AS createdAt, revoked_reason AS revokedReason,
                       CASE WHEN refresh_token_hash = ? AND is_revoked = 0 THEN 1 ELSE 0 END AS isCurrent
                FROM user_sessions
                WHERE user_id = ?
                ORDER BY isCurrent DESC, is_revoked, last_seen_at DESC, created_at DESC
                LIMIT ? OFFSET ?
                """,
                (current_refresh_token_hash, user_id, limit, offset),
            ).fetchall()
        for row in rows:
            row["isRevoked"] = bool(row["isRevoked"])
            row["isCurrent"] = bool(row["isCurrent"])
            row["riskLevel"] = self._risk_level(row)
        return rows

    @staticmethod
    def _risk_level(row: dict) -> str:
        if row.get("revokedReason") == "replay_detected":
            return "high"
        if row.get("revokedReason") in {"password_changed", "password_reset", "account_disabled"}:
            return "medium"
        if row.get("isRevoked"):
            return "ended"
        return "normal"

    def count_sessions(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM user_sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return int(row["count"])

    def revoke_session(self, user_id: int, session_uid: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = COALESCE(revoked_reason, 'logout')
                WHERE user_id = ? AND session_uid = ?
                """,
                (user_id, session_uid),
            )
            return result.rowcount > 0

    def revoke_other_sessions(self, user_id: int, current_refresh_token_hash: str | None = None) -> int:
        with self._connect() as conn:
            if current_refresh_token_hash:
                result = conn.execute(
                    """
                    UPDATE user_sessions
                    SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = COALESCE(revoked_reason, 'logout')
                    WHERE user_id = ? AND is_revoked = 0 AND refresh_token_hash != ?
                    """,
                    (user_id, current_refresh_token_hash),
                )
            else:
                result = conn.execute(
                    """
                    UPDATE user_sessions
                    SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = COALESCE(revoked_reason, 'logout')
                    WHERE user_id = ? AND is_revoked = 0
                    """,
                    (user_id,),
                )
            return result.rowcount
