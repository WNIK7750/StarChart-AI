import json
import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Any, Iterator

from app.core.security import random_uid
from app.db.database import get_connection


class SQLiteUserLearningStateRepository:
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
    def _audit(conn: Connection, user_id: int, action: str, resource_type: str, resource_id: str, metadata: dict[str, Any] | None = None) -> None:
        conn.execute(
            """
            INSERT INTO user_audit_logs(
              actor_user_id, target_user_id, action, resource_type, resource_id, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, user_id, action, resource_type, resource_id, json.dumps(metadata or {}, ensure_ascii=False)),
        )

    def list_progress(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT node_slug AS nodeSlug, status, progress_percent AS progressPercent,
                       started_at AS startedAt, completed_at AS completedAt,
                       last_studied_at AS lastStudiedAt, version, updated_at AS updatedAt
                FROM user_learning_progress WHERE user_id = ?
                ORDER BY COALESCE(last_studied_at, updated_at) DESC, id DESC
                """,
                (user_id,),
            ).fetchall()

    def get_progress(self, user_id: int, node_slug: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT node_slug AS nodeSlug, status, progress_percent AS progressPercent,
                       started_at AS startedAt, completed_at AS completedAt,
                       last_studied_at AS lastStudiedAt, version, updated_at AS updatedAt
                FROM user_learning_progress WHERE user_id = ? AND node_slug = ?
                """,
                (user_id, node_slug),
            ).fetchone()

    @staticmethod
    def _write_progress(conn: Connection, user_id: int, node_slug: str, status: str, percent: int) -> dict[str, Any]:
        conn.execute(
            """
            INSERT INTO user_learning_progress(
              user_id, node_slug, status, progress_percent, started_at, completed_at, last_studied_at
            ) VALUES (
              ?, ?, ?, ?,
              CASE WHEN ? != 'not_started' THEN CURRENT_TIMESTAMP END,
              CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP END,
              CURRENT_TIMESTAMP
            )
            ON CONFLICT(user_id, node_slug) DO UPDATE SET
              status = excluded.status,
              progress_percent = excluded.progress_percent,
              started_at = CASE
                WHEN excluded.status != 'not_started' THEN COALESCE(user_learning_progress.started_at, CURRENT_TIMESTAMP)
                ELSE user_learning_progress.started_at END,
              completed_at = CASE WHEN excluded.status = 'completed' THEN COALESCE(user_learning_progress.completed_at, CURRENT_TIMESTAMP) ELSE NULL END,
              last_studied_at = CURRENT_TIMESTAMP,
              version = user_learning_progress.version + 1,
              updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, node_slug, status, percent, status, status),
        )
        return conn.execute(
            """
            SELECT node_slug AS nodeSlug, status, progress_percent AS progressPercent,
                   started_at AS startedAt, completed_at AS completedAt,
                   last_studied_at AS lastStudiedAt, version, updated_at AS updatedAt
            FROM user_learning_progress WHERE user_id = ? AND node_slug = ?
            """,
            (user_id, node_slug),
        ).fetchone()

    def upsert_progress(
        self,
        user_id: int,
        node_slug: str,
        status: str,
        percent: int,
        expected_version: int | None,
        section_uids: list[str] | None = None,
        section_completed: bool | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT version FROM user_learning_progress WHERE user_id = ? AND node_slug = ?",
                (user_id, node_slug),
            ).fetchone()
            if expected_version is not None and (not current or int(current["version"]) != expected_version):
                raise sqlite3.IntegrityError("PROGRESS_VERSION_CONFLICT")
            if section_completed is not None:
                for section_uid in section_uids or []:
                    conn.execute(
                        """
                        INSERT INTO user_learning_section_progress(
                          user_id, node_slug, section_uid, is_completed, completed_at
                        ) VALUES (?, ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP END)
                        ON CONFLICT(user_id, section_uid) DO UPDATE SET
                          node_slug = excluded.node_slug,
                          is_completed = excluded.is_completed,
                          completed_at = CASE WHEN excluded.is_completed THEN COALESCE(user_learning_section_progress.completed_at, CURRENT_TIMESTAMP) ELSE NULL END,
                          version = user_learning_section_progress.version + 1,
                          updated_at = CURRENT_TIMESTAMP
                        """,
                        (user_id, node_slug, section_uid, int(section_completed), int(section_completed)),
                    )
            updated = self._write_progress(conn, user_id, node_slug, status, percent)
            self._audit(
                conn,
                user_id,
                "learning.progress.updated",
                "learning_progress",
                node_slug,
                {"status": status, "progressPercent": percent, "version": updated["version"]},
            )
        return updated

    def list_section_progress(self, user_id: int, node_slug: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT section_uid AS sectionUid, node_slug AS nodeSlug,
                       is_completed AS isCompleted, completed_at AS completedAt,
                       version, updated_at AS updatedAt
                FROM user_learning_section_progress
                WHERE user_id = ? AND node_slug = ? ORDER BY id
                """,
                (user_id, node_slug),
            ).fetchall()

    def set_section_progress(
        self,
        user_id: int,
        node_slug: str,
        section_uid: str,
        is_completed: bool,
        expected_version: int | None,
        total_sections: int,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT version FROM user_learning_section_progress WHERE user_id = ? AND section_uid = ?",
                (user_id, section_uid),
            ).fetchone()
            actual_version = int(current["version"]) if current else 0
            if expected_version is not None and actual_version != expected_version:
                raise sqlite3.IntegrityError("SECTION_PROGRESS_VERSION_CONFLICT")
            conn.execute(
                """
                INSERT INTO user_learning_section_progress(
                  user_id, node_slug, section_uid, is_completed, completed_at
                ) VALUES (?, ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP END)
                ON CONFLICT(user_id, section_uid) DO UPDATE SET
                  node_slug = excluded.node_slug,
                  is_completed = excluded.is_completed,
                  completed_at = CASE WHEN excluded.is_completed THEN COALESCE(user_learning_section_progress.completed_at, CURRENT_TIMESTAMP) ELSE NULL END,
                  version = user_learning_section_progress.version + 1,
                  updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, node_slug, section_uid, int(is_completed), int(is_completed)),
            )
            section = conn.execute(
                """
                SELECT section_uid AS sectionUid, node_slug AS nodeSlug,
                       is_completed AS isCompleted, completed_at AS completedAt,
                       version, updated_at AS updatedAt
                FROM user_learning_section_progress WHERE user_id = ? AND section_uid = ?
                """,
                (user_id, section_uid),
            ).fetchone()
            completed = int(conn.execute(
                "SELECT COUNT(*) AS count FROM user_learning_section_progress WHERE user_id = ? AND node_slug = ? AND is_completed = 1",
                (user_id, node_slug),
            ).fetchone()["count"])
            percent = round(completed * 100 / total_sections) if total_sections else 0
            status = "completed" if total_sections and completed >= total_sections else "in_progress" if completed else "not_started"
            progress = self._write_progress(conn, user_id, node_slug, status, percent)
            self._audit(
                conn, user_id, "learning.section_progress.updated", "learning_section", section_uid,
                {"nodeSlug": node_slug, "isCompleted": is_completed, "version": section["version"]},
            )
            self._audit(
                conn, user_id, "learning.progress.updated", "learning_progress", node_slug,
                {"status": status, "progressPercent": percent, "version": progress["version"], "source": "section_progress"},
            )
            return {"section": section, "progress": progress, "completedCount": completed}

    def record_activity(self, user_id: int, item: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            if item.get("idempotencyKey"):
                existing = conn.execute(
                    """
                    SELECT activity_uid AS activityUid, node_slug AS nodeSlug, target_type AS targetType,
                           target_key AS targetKey, activity_type AS activityType, created_at AS createdAt
                    FROM user_learning_activity WHERE user_id = ? AND idempotency_key = ?
                    """,
                    (user_id, item["idempotencyKey"]),
                ).fetchone()
                if existing:
                    return {**existing, "idempotencyReplayed": True}
            activity_uid = random_uid("act")
            conn.execute(
                """
                INSERT INTO user_learning_activity(
                  activity_uid, user_id, node_slug, target_type, target_key,
                  activity_type, metadata_json, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_uid,
                    user_id,
                    item.get("nodeSlug"),
                    item["targetType"],
                    item["targetKey"],
                    item["activityType"],
                    json.dumps(item.get("metadata") or {}, ensure_ascii=False),
                    item.get("idempotencyKey"),
                ),
            )
            created = conn.execute(
                """
                SELECT activity_uid AS activityUid, node_slug AS nodeSlug, target_type AS targetType,
                       target_key AS targetKey, activity_type AS activityType, created_at AS createdAt
                FROM user_learning_activity WHERE activity_uid = ?
                """,
                (activity_uid,),
            ).fetchone()
            return {**created, "idempotencyReplayed": False}

    def recent(self, user_id: int, limit: int, offset: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT a.activity_uid AS activityUid, a.node_slug AS nodeSlug,
                       a.target_type AS targetType, a.target_key AS targetKey,
                       a.activity_type AS activityType, a.created_at AS lastReadAt
                FROM user_learning_activity a
                JOIN (
                  SELECT target_type, target_key, MAX(id) AS latest_id
                  FROM user_learning_activity WHERE user_id = ?
                  GROUP BY target_type, target_key
                ) latest ON latest.latest_id = a.id
                ORDER BY a.id DESC LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()

    def recent_count(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count FROM (
                  SELECT 1 FROM user_learning_activity WHERE user_id = ? GROUP BY target_type, target_key
                )
                """,
                (user_id,),
            ).fetchone()
            return int(row["count"])

    def list_favorites(self, user_id: int, limit: int, offset: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT favorite_uid AS favoriteUid, target_type AS targetType, target_key AS targetKey,
                       title_snapshot AS titleSnapshot, description_snapshot AS descriptionSnapshot,
                       created_at AS createdAt
                FROM user_favorites WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()

    def favorites_count(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM user_favorites WHERE user_id = ?", (user_id,)).fetchone()
            return int(row["count"])

    def add_favorite(self, user_id: int, item: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            favorite_uid = random_uid("fav")
            inserted = conn.execute(
                """
                INSERT INTO user_favorites(
                  favorite_uid, user_id, target_type, target_key, title_snapshot, description_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, target_type, target_key) DO NOTHING
                """,
                (favorite_uid, user_id, item["targetType"], item["targetKey"], item["title"], item.get("description")),
            )
            favorite = conn.execute(
                """
                SELECT favorite_uid AS favoriteUid, target_type AS targetType, target_key AS targetKey,
                       title_snapshot AS titleSnapshot, description_snapshot AS descriptionSnapshot,
                       created_at AS createdAt
                FROM user_favorites WHERE user_id = ? AND target_type = ? AND target_key = ?
                """,
                (user_id, item["targetType"], item["targetKey"]),
            ).fetchone()
            if inserted.rowcount:
                self._audit(
                    conn,
                    user_id,
                    "favorite.added",
                    "favorite",
                    favorite["favoriteUid"],
                    {"targetType": item["targetType"], "targetKey": item["targetKey"]},
                )
            return favorite

    def remove_favorite(self, user_id: int, favorite_uid: str) -> bool:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            favorite = conn.execute(
                "SELECT target_type AS targetType, target_key AS targetKey FROM user_favorites WHERE user_id = ? AND favorite_uid = ?",
                (user_id, favorite_uid),
            ).fetchone()
            result = conn.execute(
                "DELETE FROM user_favorites WHERE user_id = ? AND favorite_uid = ?", (user_id, favorite_uid)
            )
            if result.rowcount and favorite:
                self._audit(
                    conn,
                    user_id,
                    "favorite.removed",
                    "favorite",
                    favorite_uid,
                    favorite,
                )
            return result.rowcount > 0
