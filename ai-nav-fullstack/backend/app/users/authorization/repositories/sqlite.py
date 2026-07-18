from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteAuthorizationRepository:
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

    def list_role_codes(self, user_id: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.code
                FROM user_role_assignments ura
                JOIN roles r ON r.id = ura.role_id
                WHERE ura.user_id = ? AND (ura.expires_at IS NULL OR ura.expires_at > CURRENT_TIMESTAMP)
                ORDER BY r.code
                """,
                (user_id,),
            ).fetchall()
            return [row["code"] for row in rows]

    def list_permission_codes(self, user_id: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT p.code
                FROM user_role_assignments ura
                JOIN role_permissions rp ON rp.role_id = ura.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ura.user_id = ? AND (ura.expires_at IS NULL OR ura.expires_at > CURRENT_TIMESTAMP)
                ORDER BY p.code
                """,
                (user_id,),
            ).fetchall()
            return [row["code"] for row in rows]
