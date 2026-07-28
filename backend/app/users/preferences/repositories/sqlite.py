from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


PREFERENCE_COLUMNS = {
    "theme": "theme",
    "language": "language",
    "cnFirst": "cn_first",
    "freeFirst": "free_first",
    "showExternalResources": "show_external_resources",
    "agentMemoryEnabled": "agent_memory_enabled",
}


class SQLitePreferencesRepository:
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

    @staticmethod
    def _select(conn: Connection, user_id: int) -> dict | None:
        row = conn.execute(
            """
            SELECT theme, language, cn_first AS cnFirst, free_first AS freeFirst,
                   show_external_resources AS showExternalResources,
                   agent_memory_enabled AS agentMemoryEnabled,
                   preference_json AS preferenceJson, version, updated_at AS updatedAt
            FROM user_preferences
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row:
            for key in ("cnFirst", "freeFirst", "showExternalResources", "agentMemoryEnabled"):
                row[key] = bool(row[key])
        return row

    def get_preferences(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            return self._select(conn, user_id)

    def update_preferences(self, user_id: int, values: dict, expected_version: int) -> tuple[dict | None, bool]:
        with self._connect() as conn:
            if values:
                assignments = []
                params = []
                for key, value in values.items():
                    assignments.append(f"{PREFERENCE_COLUMNS[key]} = ?")
                    params.append(int(value) if isinstance(value, bool) else value)
                params.extend((user_id, expected_version))
                cursor = conn.execute(
                    f"UPDATE user_preferences SET {', '.join(assignments)}, version = version + 1, "
                    "updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND version = ?",
                    params,
                )
                return self._select(conn, user_id), cursor.rowcount == 1
            preferences = self._select(conn, user_id)
            return preferences, bool(preferences and preferences["version"] == expected_version)
