from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.core.security import hash_password, needs_password_rehash, verify_password
from app.db.database import get_connection


class SQLiteSecurityRepository:
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

    def update_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT password_hash FROM user_auth_passwords WHERE user_id = ?", (user_id,)).fetchone()
            if not row or not verify_password(current_password, row["password_hash"]):
                return False
            conn.execute(
                """
                UPDATE user_auth_passwords
                SET password_hash = ?, failed_attempts = 0, locked_until = NULL,
                    password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (hash_password(new_password), user_id),
            )
            conn.execute(
                "UPDATE user_accounts SET token_version = token_version + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,),
            )
            conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = 'password_changed'
                WHERE user_id = ? AND is_revoked = 0
                """,
                (user_id,),
            )
            return True

    def list_security_questions(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT question_order AS questionOrder, question_text AS question, updated_at AS updatedAt
                FROM user_security_questions
                WHERE user_id = ?
                ORDER BY question_order
                """,
                (user_id,),
            ).fetchall()

    def replace_security_questions(self, user_id: int, current_password: str, questions: list[tuple[int, str, str]]) -> list[dict] | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT password_hash FROM user_auth_passwords WHERE user_id = ?", (user_id,)).fetchone()
            if not row or not verify_password(current_password, row["password_hash"]):
                return None
            if needs_password_rehash(row["password_hash"]):
                conn.execute(
                    """
                    UPDATE user_auth_passwords
                    SET password_hash = ?, password_algo = 'pbkdf2_sha256',
                        password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (hash_password(current_password), user_id),
                )
            conn.execute("DELETE FROM user_security_questions WHERE user_id = ?", (user_id,))
            conn.executemany(
                """
                INSERT INTO user_security_questions(user_id, question_order, question_text, answer_hash)
                VALUES (?, ?, ?, ?)
                """,
                [(user_id, order, question, answer_hash) for order, question, answer_hash in questions],
            )
            return conn.execute(
                """
                SELECT question_order AS questionOrder, question_text AS question, updated_at AS updatedAt
                FROM user_security_questions
                WHERE user_id = ?
                ORDER BY question_order
                """,
                (user_id,),
            ).fetchall()
