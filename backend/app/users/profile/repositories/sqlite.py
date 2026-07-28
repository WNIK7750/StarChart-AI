from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


PROFILE_COLUMNS = {
    "displayName": "display_name",
    "bio": "bio",
    "roleTitle": "role_title",
    "learningLevel": "learning_level",
    "targetDirection": "target_direction",
}


class SQLiteProfileRepository:
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
        return conn.execute(
            """
            SELECT display_name AS displayName, avatar_url AS avatarUrl, bio,
                   role_title AS roleTitle, learning_level AS learningLevel,
                   target_direction AS targetDirection, version, updated_at AS updatedAt
            FROM user_profiles
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    def get_profile(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            return self._select(conn, user_id)

    def update_profile(self, user_id: int, values: dict, expected_version: int) -> tuple[dict | None, bool]:
        with self._connect() as conn:
            if values:
                assignments = []
                params = []
                for key, value in values.items():
                    assignments.append(f"{PROFILE_COLUMNS[key]} = ?")
                    params.append(value)
                params.extend((user_id, expected_version))
                cursor = conn.execute(
                    f"UPDATE user_profiles SET {', '.join(assignments)}, version = version + 1, "
                    "updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND version = ?",
                    params,
                )
                return self._select(conn, user_id), cursor.rowcount == 1
            profile = self._select(conn, user_id)
            return profile, bool(profile and profile["version"] == expected_version)

    def update_avatar(self, user_id: int, avatar_url: str) -> tuple[str | None, dict]:
        with self._connect() as conn:
            old = conn.execute("SELECT avatar_url AS avatarUrl FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
            conn.execute(
                "UPDATE user_profiles SET avatar_url = ?, version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (avatar_url, user_id),
            )
            return (old["avatarUrl"] if old else None, self._select(conn, user_id))
