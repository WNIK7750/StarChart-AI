from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteAgentModelSettingsRepository:
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
            SELECT provider_key AS providerKey, provider_name AS providerName,
                   base_url AS baseUrl, model_display_name AS modelDisplayName,
                   model_id AS modelId,
                   max_output_tokens AS maxOutputTokens, enabled,
                   connection_status AS connectionStatus,
                   connection_error_code AS connectionErrorCode,
                   connection_checked_at AS connectionCheckedAt,
                   version, created_at AS createdAt, updated_at AS updatedAt
            FROM user_agent_model_settings WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row:
            row["enabled"] = bool(row["enabled"])
        return row

    def get(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            return self._select(conn, user_id)

    def upsert(
        self,
        user_id: int,
        values: dict,
        expected_version: int | None,
    ) -> tuple[dict | None, bool]:
        with self._connect() as conn:
            current = self._select(conn, user_id)
            if current is None:
                if expected_version is not None:
                    return None, False
                conn.execute(
                    """
                    INSERT INTO user_agent_model_settings(
                      user_id, provider_key, provider_name, base_url,
                      model_display_name, model_id,
                      max_output_tokens, enabled,
                      connection_status, connection_error_code,
                      connection_checked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id, values["providerKey"], values["providerName"],
                        values["baseUrl"], values["modelDisplayName"],
                        values["modelId"], values["maxOutputTokens"],
                        int(values["enabled"]),
                        values["connectionStatus"], values.get("connectionErrorCode"),
                        values.get("connectionCheckedAt"),
                    ),
                )
                return self._select(conn, user_id), True
            if expected_version != current["version"]:
                return current, False
            cursor = conn.execute(
                """
                UPDATE user_agent_model_settings
                SET provider_key = ?, provider_name = ?, base_url = ?,
                    model_display_name = ?, model_id = ?,
                    max_output_tokens = ?, enabled = ?,
                    connection_status = ?, connection_error_code = ?,
                    connection_checked_at = ?, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND version = ?
                """,
                (
                    values["providerKey"], values["providerName"], values["baseUrl"],
                    values["modelDisplayName"], values["modelId"],
                    values["maxOutputTokens"], int(values["enabled"]),
                    values["connectionStatus"],
                    values.get("connectionErrorCode"), values.get("connectionCheckedAt"),
                    user_id, expected_version,
                ),
            )
            return self._select(conn, user_id), cursor.rowcount == 1

    def delete(self, user_id: int) -> bool:
        with self._connect() as conn:
            return conn.execute(
                "DELETE FROM user_agent_model_settings WHERE user_id = ?",
                (user_id,),
            ).rowcount == 1
