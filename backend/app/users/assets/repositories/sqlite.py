from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteAssetsRepository:
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
    def _workflow(conn: Connection, row: dict | None) -> dict | None:
        if not row:
            return None
        steps = conn.execute(
            """
            SELECT step_uid AS stepUid, step_order AS stepOrder, name, objective,
                   tool_slug AS toolSlug, tool_name_snapshot AS toolNameSnapshot,
                   tool_href_snapshot AS toolHrefSnapshot
            FROM user_saved_workflow_steps
            WHERE workflow_id = ? ORDER BY step_order
            """,
            (row["id"],),
        ).fetchall()
        return {
            "workflowUid": row["workflow_uid"],
            "title": row["title"],
            "description": row["description"],
            "sourceType": row["source_type"],
            "sourceRef": row["source_ref"],
            "status": row["status"],
            "version": row["version"],
            "archivedAt": row["archived_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "steps": steps,
        }

    def create_workflow(self, user_id: int, workflow_uid: str, idempotency_key: str, data: dict, steps: list[dict]) -> tuple[dict, bool]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM user_saved_workflows WHERE user_id = ? AND idempotency_key = ?",
                (user_id, idempotency_key),
            ).fetchone()
            if existing:
                return self._workflow(conn, existing), True
            cursor = conn.execute(
                """
                INSERT INTO user_saved_workflows(
                    workflow_uid, user_id, title, description, source_type,
                    source_ref, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_uid,
                    user_id,
                    data["title"],
                    data.get("description"),
                    data["sourceType"],
                    data.get("sourceRef"),
                    idempotency_key,
                ),
            )
            workflow_id = cursor.lastrowid
            conn.executemany(
                """
                INSERT INTO user_saved_workflow_steps(
                    step_uid, workflow_id, step_order, name, objective,
                    tool_slug, tool_name_snapshot, tool_href_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        step["stepUid"],
                        workflow_id,
                        step["order"],
                        step["name"],
                        step["objective"],
                        step.get("toolSlug"),
                        step.get("toolNameSnapshot"),
                        step.get("toolHrefSnapshot"),
                    )
                    for step in steps
                ],
            )
            created = conn.execute("SELECT * FROM user_saved_workflows WHERE id = ?", (workflow_id,)).fetchone()
            return self._workflow(conn, created), False

    def get_workflow(self, user_id: int, workflow_uid: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM user_saved_workflows WHERE user_id = ? AND workflow_uid = ?",
                (user_id, workflow_uid),
            ).fetchone()
            return self._workflow(conn, row)

    def list_workflows(self, user_id: int, status: str, limit: int, offset: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM user_saved_workflows
                WHERE user_id = ? AND (? = 'all' OR status = ?)
                ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?
                """,
                (user_id, status, status, limit, offset),
            ).fetchall()
            return [self._workflow(conn, row) for row in rows]

    def count_workflows(self, user_id: int, status: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count FROM user_saved_workflows
                WHERE user_id = ? AND (? = 'all' OR status = ?)
                """,
                (user_id, status, status),
            ).fetchone()
            return int(row["count"])

    def update_workflow(self, user_id: int, workflow_uid: str, expected_version: int, values: dict) -> tuple[dict | None, bool]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM user_saved_workflows WHERE user_id = ? AND workflow_uid = ?",
                (user_id, workflow_uid),
            ).fetchone()
            if not row:
                return None, False
            updates = []
            params = []
            for field, column in (("title", "title"), ("description", "description")):
                if field in values and values[field] is not None:
                    updates.append(f"{column} = ?")
                    params.append(values[field])
            if not updates:
                return self._workflow(conn, row), True
            params.extend([user_id, workflow_uid, expected_version])
            result = conn.execute(
                f"""
                UPDATE user_saved_workflows
                SET {', '.join(updates)}, version = version + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND workflow_uid = ? AND version = ?
                """,
                params,
            )
            current = conn.execute(
                "SELECT * FROM user_saved_workflows WHERE user_id = ? AND workflow_uid = ?",
                (user_id, workflow_uid),
            ).fetchone()
            return self._workflow(conn, current), bool(result.rowcount)

    def set_workflow_status(self, user_id: int, workflow_uid: str, expected_version: int, status: str) -> tuple[dict | None, bool]:
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE user_saved_workflows
                SET status = ?, archived_at = CASE WHEN ? = 'archived' THEN CURRENT_TIMESTAMP ELSE NULL END,
                    version = version + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND workflow_uid = ? AND version = ?
                """,
                (status, status, user_id, workflow_uid, expected_version),
            )
            row = conn.execute(
                "SELECT * FROM user_saved_workflows WHERE user_id = ? AND workflow_uid = ?",
                (user_id, workflow_uid),
            ).fetchone()
            return self._workflow(conn, row), bool(result.rowcount)
