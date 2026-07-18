from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteAccountRepository:
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

    def get_account(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT user_uid AS userUid, username, email, phone,
                       email_verified AS emailVerified, phone_verified AS phoneVerified,
                       account_status AS accountStatus, updated_at AS updatedAt
                FROM user_accounts
                WHERE id = ? AND deleted_at IS NULL
                """,
                (user_id,),
            ).fetchone()

    def is_username_available(self, username: str, exclude_user_id: int | None = None) -> bool:
        query = "SELECT id FROM user_accounts WHERE lower(username) = lower(?) AND deleted_at IS NULL"
        params: tuple = (username,)
        if exclude_user_id is not None:
            query += " AND id != ?"
            params = (username, exclude_user_id)
        with self._connect() as conn:
            return conn.execute(query, params).fetchone() is None

    def _is_identity_available(self, column: str, value: str, exclude_user_id: int | None) -> bool:
        expression = f"lower({column})" if column == "email" else column
        query = f"SELECT id FROM user_accounts WHERE {expression} = ? AND deleted_at IS NULL"
        params: tuple = (value.lower() if column == "email" else value,)
        if exclude_user_id is not None:
            query += " AND id != ?"
            params += (exclude_user_id,)
        with self._connect() as conn:
            return conn.execute(query, params).fetchone() is None

    def is_email_available(self, email: str, exclude_user_id: int | None = None) -> bool:
        return self._is_identity_available("email", email, exclude_user_id)

    def is_phone_available(self, phone: str, exclude_user_id: int | None = None) -> bool:
        return self._is_identity_available("phone", phone, exclude_user_id)

    def get_password_hash(self, user_id: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT password_hash FROM user_auth_passwords WHERE user_id = ?", (user_id,)).fetchone()
            return row["password_hash"] if row else None

    def update_account(self, user_id: int, username: str, email: str | None, phone: str | None) -> dict:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE user_accounts
                SET username = ?, email = ?, phone = ?,
                    email_verified = CASE WHEN email IS ? THEN email_verified ELSE 0 END,
                    phone_verified = CASE WHEN phone IS ? THEN phone_verified ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND deleted_at IS NULL
                """,
                (username, email, phone, email, phone, user_id),
            )
            return conn.execute(
                """
                SELECT user_uid AS userUid, username, email, phone,
                       email_verified AS emailVerified, phone_verified AS phoneVerified,
                       account_status AS accountStatus, updated_at AS updatedAt
                FROM user_accounts
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
