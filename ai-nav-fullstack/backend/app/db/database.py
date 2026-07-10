import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.core.config import DATABASE_PATH, LEARNING_CONTENT_PATH, RESET_DATABASE_ON_START, SCHEMA_PATH, SEED_PATH


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    should_reset = RESET_DATABASE_ON_START and DATABASE_PATH.exists()
    if should_reset:
        DATABASE_PATH.unlink()
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        has_navigation = conn.execute("SELECT COUNT(*) FROM navigation_items").fetchone()[0] > 0
        if not has_navigation:
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))

        has_learning_materials = conn.execute("SELECT COUNT(*) FROM learning_materials").fetchone()[0] > 0
        if LEARNING_CONTENT_PATH.exists() and not has_learning_materials:
            conn.executescript(LEARNING_CONTENT_PATH.read_text(encoding="utf-8"))

        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(user_accounts)").fetchall()}
        if "token_version" not in user_columns:
            conn.execute(
                "ALTER TABLE user_accounts ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0 CHECK (token_version >= 0)"
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_security_questions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              question_order INTEGER NOT NULL CHECK (question_order BETWEEN 1 AND 3),
              question_text TEXT NOT NULL,
              answer_hash TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES user_accounts(id),
              UNIQUE (user_id, question_order)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_security_questions_user
            ON user_security_questions(user_id, question_order)
            """
        )
