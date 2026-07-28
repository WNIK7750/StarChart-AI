import sqlite3
import hashlib
import re
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import DATABASE_PATH, LEARNING_CONTENT_PATH, MIGRATIONS_DIR, RESET_DATABASE_ON_START, SCHEMA_PATH, SEED_PATH


ADD_COLUMN_DIRECTIVE = re.compile(
    r"^\s*--\s*ai-nav:add-column-if-missing\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*$",
    re.MULTILINE,
)


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def _row_value(row, index: int, key: str):
    return row[key] if isinstance(row, dict) else row[index]


def _execute_migration_statements(conn: sqlite3.Connection, source: str) -> None:
    statement = ""
    for line in source.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            if statement.strip():
                conn.execute(statement)
            statement = ""
    if statement.strip():
        raise RuntimeError("Migration contains an incomplete SQL statement")


def _apply_conditional_columns(conn: sqlite3.Connection, source: str) -> None:
    for table, column, definition in ADD_COLUMN_DIRECTIVE.findall(source):
        if ";" in definition or "--" in definition:
            raise RuntimeError("Conditional migration column definition contains forbidden syntax")
        columns = {
            _row_value(row, 1, "name")
            for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        }
        if not columns:
            raise RuntimeError(f"Conditional migration table does not exist: {table}")
        if column not in columns:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}')


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, timeout=5.0)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def db_cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_migrations(conn: sqlite3.Connection, migrations_dir: Path) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          checksum TEXT,
          applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {
        _row_value(row, 1, "name")
        for row in conn.execute("PRAGMA table_info(schema_migrations)").fetchall()
    }
    if "checksum" not in columns:
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN checksum TEXT")
    conn.commit()
    if not migrations_dir.exists():
        return

    for migration in sorted(migrations_dir.glob("*.sql")):
        source = migration.read_text(encoding="utf-8")
        checksum = hashlib.sha256(source.encode("utf-8")).hexdigest()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT checksum FROM schema_migrations WHERE version = ?",
                (migration.name,),
            ).fetchone()
            if row is not None:
                previous = _row_value(row, 0, "checksum")
                if previous and previous != checksum:
                    raise RuntimeError(f"Applied migration checksum mismatch: {migration.name}")
                if previous is None:
                    conn.execute(
                        "UPDATE schema_migrations SET checksum = ? WHERE version = ?",
                        (checksum, migration.name),
                    )
                conn.commit()
                continue
            _apply_conditional_columns(conn, source)
            _execute_migration_statements(conn, source)
            conn.execute(
                "INSERT INTO schema_migrations(version, checksum) VALUES (?, ?)",
                (migration.name, checksum),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    should_reset = RESET_DATABASE_ON_START and DATABASE_PATH.exists()
    if should_reset:
        DATABASE_PATH.unlink()
    with closing(sqlite3.connect(DATABASE_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        has_navigation = conn.execute("SELECT COUNT(*) FROM navigation_items").fetchone()[0] > 0
        if not has_navigation:
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))

        has_learning_materials = conn.execute("SELECT COUNT(*) FROM learning_materials").fetchone()[0] > 0
        if LEARNING_CONTENT_PATH.exists() and not has_learning_materials:
            conn.executescript(LEARNING_CONTENT_PATH.read_text(encoding="utf-8"))

        apply_migrations(conn, MIGRATIONS_DIR)
