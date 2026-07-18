import json
from collections.abc import Callable
from sqlite3 import Connection

from app.db.database import get_connection


class SQLiteAuditRepository:
    def __init__(self, connection_factory: Callable[[], Connection] = get_connection):
        self._connection_factory = connection_factory

    def append(
        self,
        *,
        actor_user_id: int | None,
        target_user_id: int | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        metadata: dict,
    ) -> int:
        conn = self._connection_factory()
        try:
            cursor = conn.execute(
                """
                INSERT INTO user_audit_logs(
                    actor_user_id, target_user_id, action, resource_type, resource_id,
                    ip_address, user_agent, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    actor_user_id,
                    target_user_id,
                    action,
                    resource_type,
                    resource_id,
                    ip_address[:64] if ip_address else None,
                    user_agent[:512] if user_agent else None,
                    json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
