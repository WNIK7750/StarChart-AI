from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from sqlite3 import Connection
from typing import Iterator
from uuid import uuid4

from app.db.database import get_connection
from app.core.config import AGENT_SESSION_RETENTION_DAYS
from app.agent.schemas import AgentHistoryMessage
from app.agent.conversation_context import compact_conversation_history


_UNCHANGED = object()
LONG_CONVERSATION_LIMIT = 3


class AgentSessionError(Exception):
    def __init__(self, code: str, message: str, status_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AgentSessionStore:
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
    def _summary(row: dict) -> dict:
        return {
            "sessionId": row["session_uid"],
            "title": row["title"],
            "messageCount": int(row["message_count"]),
            "pinned": bool(row["pinned_at"]),
            "pinnedAt": row["pinned_at"],
            "expiresAt": row["expires_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    @staticmethod
    def _long_summary(row: dict) -> dict:
        return {
            "conversationId": row["conversation_uid"],
            "title": row["title"],
            "messageCount": int(row["message_count"]),
            "pinned": bool(row["pinned_at"]),
            "pinnedAt": row["pinned_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def create(
        self,
        user_id: int,
        session_uid: str,
        title: str,
        expires_at: str,
    ) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                DELETE FROM agent_chat_sessions
                WHERE user_id = ? AND expires_at <= CURRENT_TIMESTAMP
                """,
                (user_id,),
            )
            unstarted = conn.execute(
                """
                SELECT 1
                FROM agent_chat_sessions s
                WHERE s.user_id = ? AND s.expires_at > CURRENT_TIMESTAMP
                  AND NOT EXISTS (
                    SELECT 1 FROM agent_chat_messages m WHERE m.session_id = s.id
                  )
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            if unstarted:
                return None
            cursor = conn.execute(
                """
                INSERT INTO agent_chat_sessions(
                    session_uid, user_id, title, expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (session_uid, user_id, title, expires_at),
            )
            row = conn.execute(
                """
                SELECT s.*, 0 AS message_count
                FROM agent_chat_sessions s WHERE s.id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            return self._summary(row)

    def ensure_draft(
        self,
        user_id: int,
        session_uid: str,
        title: str,
        expires_at: str,
    ) -> dict:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                DELETE FROM agent_chat_sessions
                WHERE user_id = ? AND expires_at <= CURRENT_TIMESTAMP
                """,
                (user_id,),
            )
            row = conn.execute(
                """
                SELECT s.*, 0 AS message_count
                FROM agent_chat_sessions s
                WHERE s.user_id = ? AND s.expires_at > CURRENT_TIMESTAMP
                  AND NOT EXISTS (
                    SELECT 1 FROM agent_chat_messages m WHERE m.session_id = s.id
                  )
                ORDER BY s.updated_at DESC, s.id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            if row:
                return self._summary(row)
            cursor = conn.execute(
                """
                INSERT INTO agent_chat_sessions(
                    session_uid, user_id, title, expires_at
                ) VALUES (?, ?, ?, ?)
                """,
                (session_uid, user_id, title, expires_at),
            )
            created = conn.execute(
                """
                SELECT s.*, 0 AS message_count
                FROM agent_chat_sessions s WHERE s.id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            return self._summary(created)

    def list(self, user_id: int, limit: int, offset: int) -> tuple[list[dict], int]:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM agent_chat_sessions
                WHERE user_id = ? AND expires_at <= CURRENT_TIMESTAMP
                """,
                (user_id,),
            )
            rows = conn.execute(
                """
                SELECT s.*, COUNT(m.id) AS message_count
                FROM agent_chat_sessions s
                LEFT JOIN agent_chat_messages m ON m.session_id = s.id
                WHERE s.user_id = ?
                GROUP BY s.id
                ORDER BY
                  CASE WHEN s.pinned_at IS NULL THEN 1 ELSE 0 END,
                  s.pinned_at DESC,
                  s.updated_at DESC,
                  s.id DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) AS count FROM agent_chat_sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return [self._summary(row) for row in rows], int(total["count"])

    def get(
        self,
        user_id: int,
        session_uid: str,
        message_limit: int,
        message_offset: int,
    ) -> tuple[dict, list[dict], int] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.*, COUNT(m.id) AS message_count
                FROM agent_chat_sessions s
                LEFT JOIN agent_chat_messages m ON m.session_id = s.id
                WHERE s.user_id = ? AND s.session_uid = ?
                  AND s.expires_at > CURRENT_TIMESTAMP
                GROUP BY s.id
                """,
                (user_id, session_uid),
            ).fetchone()
            if not row:
                return None
            messages = conn.execute(
                """
                SELECT message_uid AS messageId, role, content, created_at AS createdAt
                FROM agent_chat_messages
                WHERE session_id = ?
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (row["id"], message_limit, message_offset),
            ).fetchall()
            return self._summary(row), messages, int(row["message_count"])

    def context(
        self,
        user_id: int,
        session_uid: str,
        limit: int,
    ) -> list[dict] | None:
        with self._connect() as conn:
            message_table: str
            parent_column: str
            parent_id: int
            if session_uid.startswith("agl_"):
                parent = conn.execute(
                    """
                    SELECT id
                    FROM agent_long_conversations
                    WHERE user_id = ? AND conversation_uid = ?
                    """,
                    (user_id, session_uid),
                ).fetchone()
                if not parent:
                    return None
                message_table = "agent_long_conversation_messages"
                parent_column = "conversation_id"
                parent_id = parent["id"]
            else:
                parent = conn.execute(
                    """
                    SELECT id
                    FROM agent_chat_sessions
                    WHERE user_id = ? AND session_uid = ?
                      AND expires_at > CURRENT_TIMESTAMP
                    """,
                    (user_id, session_uid),
                ).fetchone()
                if parent:
                    message_table = "agent_chat_messages"
                    parent_column = "session_id"
                    parent_id = parent["id"]
                else:
                    parent = conn.execute(
                        """
                        SELECT id
                        FROM agent_long_conversations
                        WHERE user_id = ? AND source_session_uid = ?
                        """,
                        (user_id, session_uid),
                    ).fetchone()
                    if not parent:
                        return None
                    message_table = "agent_long_conversation_messages"
                    parent_column = "conversation_id"
                    parent_id = parent["id"]
            rows = conn.execute(
                f"""
                SELECT role, content
                FROM {message_table}
                WHERE {parent_column} = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (parent_id, limit),
            ).fetchall()
            return list(reversed(rows))

    def append_exchange(
        self,
        user_id: int,
        session_uid: str,
        request_id: str,
        user_message: str,
        assistant_message: str,
        expires_at: str,
    ) -> bool | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            session = conn.execute(
                """
                SELECT id, title, title_customized FROM agent_chat_sessions
                WHERE user_id = ? AND session_uid = ?
                  AND expires_at > CURRENT_TIMESTAMP
                """,
                (user_id, session_uid),
            ).fetchone()
            if not session:
                return None
            existing = conn.execute(
                """
                SELECT 1 FROM agent_chat_messages
                WHERE session_id = ? AND request_id = ? AND role = 'assistant'
                """,
                (session["id"], request_id),
            ).fetchone()
            if existing:
                return False
            conn.executemany(
                """
                INSERT INTO agent_chat_messages(
                    message_uid, session_id, role, content, request_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (
                        f"msg_{uuid4().hex}",
                        session["id"],
                        "user",
                        user_message,
                        request_id,
                    ),
                    (
                        f"msg_{uuid4().hex}",
                        session["id"],
                        "assistant",
                        assistant_message,
                        request_id,
                    ),
                ),
            )
            title = session["title"]
            if not bool(session["title_customized"]):
                title = user_message[:40]
            conn.execute(
                """
                UPDATE agent_chat_sessions
                SET title = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, expires_at, session["id"]),
            )
            return True

    def update(
        self,
        user_id: int,
        session_uid: str,
        *,
        title: str | None,
        pinned_at: str | None | object,
    ) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            session = conn.execute(
                """
                SELECT id FROM agent_chat_sessions
                WHERE user_id = ? AND session_uid = ?
                  AND expires_at > CURRENT_TIMESTAMP
                """,
                (user_id, session_uid),
            ).fetchone()
            if not session:
                return None
            assignments = ["updated_at = CURRENT_TIMESTAMP"]
            values: list[object] = []
            if title is not None:
                assignments.extend(("title = ?", "title_customized = 1"))
                values.append(title)
            if pinned_at is not _UNCHANGED:
                assignments.append("pinned_at = ?")
                values.append(pinned_at)
            values.append(session["id"])
            conn.execute(
                f"UPDATE agent_chat_sessions SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
            row = conn.execute(
                """
                SELECT s.*, COUNT(m.id) AS message_count
                FROM agent_chat_sessions s
                LEFT JOIN agent_chat_messages m ON m.session_id = s.id
                WHERE s.id = ?
                GROUP BY s.id
                """,
                (session["id"],),
            ).fetchone()
            return self._summary(row)

    def delete(self, user_id: int, session_uid: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM agent_chat_sessions WHERE user_id = ? AND session_uid = ?",
                (user_id, session_uid),
            )
            return bool(result.rowcount)

    def upgrade(
        self,
        user_id: int,
        session_uid: str,
        conversation_uid: str,
        limit: int,
    ) -> tuple[str, dict | None]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT c.*, COUNT(m.id) AS message_count
                FROM agent_long_conversations c
                LEFT JOIN agent_long_conversation_messages m
                  ON m.conversation_id = c.id
                WHERE c.user_id = ? AND c.source_session_uid = ?
                GROUP BY c.id
                """,
                (user_id, session_uid),
            ).fetchone()
            if existing:
                return "existing", self._long_summary(existing)

            session = conn.execute(
                """
                SELECT s.*, COUNT(m.id) AS message_count
                FROM agent_chat_sessions s
                LEFT JOIN agent_chat_messages m ON m.session_id = s.id
                WHERE s.user_id = ? AND s.session_uid = ?
                  AND s.expires_at > CURRENT_TIMESTAMP
                GROUP BY s.id
                """,
                (user_id, session_uid),
            ).fetchone()
            if not session:
                return "missing", None
            if int(session["message_count"]) < 2:
                return "unstarted", None
            total = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM agent_long_conversations
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if int(total["count"]) >= limit:
                return "limit", None

            cursor = conn.execute(
                """
                INSERT INTO agent_long_conversations(
                    conversation_uid, user_id, source_session_uid, title,
                    pinned_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_uid,
                    user_id,
                    session_uid,
                    session["title"],
                    session["pinned_at"],
                    session["created_at"],
                    session["updated_at"],
                ),
            )
            messages = conn.execute(
                """
                SELECT role, content, request_id, created_at
                FROM agent_chat_messages
                WHERE session_id = ?
                ORDER BY id
                """,
                (session["id"],),
            ).fetchall()
            conn.executemany(
                """
                INSERT INTO agent_long_conversation_messages(
                    message_uid, conversation_id, role, content, request_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        f"lgm_{uuid4().hex}",
                        cursor.lastrowid,
                        message["role"],
                        message["content"],
                        message["request_id"],
                        message["created_at"],
                    )
                    for message in messages
                ),
            )
            conn.execute(
                "DELETE FROM agent_chat_sessions WHERE id = ?",
                (session["id"],),
            )
            row = conn.execute(
                """
                SELECT c.*, COUNT(m.id) AS message_count
                FROM agent_long_conversations c
                LEFT JOIN agent_long_conversation_messages m
                  ON m.conversation_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
                """,
                (cursor.lastrowid,),
            ).fetchone()
            return "created", self._long_summary(row)

    def list_long(
        self,
        user_id: int,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, COUNT(m.id) AS message_count
                FROM agent_long_conversations c
                LEFT JOIN agent_long_conversation_messages m
                  ON m.conversation_id = c.id
                WHERE c.user_id = ?
                GROUP BY c.id
                ORDER BY
                  CASE WHEN c.pinned_at IS NULL THEN 1 ELSE 0 END,
                  c.pinned_at DESC,
                  c.updated_at DESC,
                  c.id DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset),
            ).fetchall()
            total = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM agent_long_conversations
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return [self._long_summary(row) for row in rows], int(total["count"])

    def get_long(
        self,
        user_id: int,
        conversation_uid: str,
        message_limit: int,
        message_offset: int,
    ) -> tuple[dict, list[dict], int] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT c.*, COUNT(m.id) AS message_count
                FROM agent_long_conversations c
                LEFT JOIN agent_long_conversation_messages m
                  ON m.conversation_id = c.id
                WHERE c.user_id = ? AND c.conversation_uid = ?
                GROUP BY c.id
                """,
                (user_id, conversation_uid),
            ).fetchone()
            if not row:
                return None
            messages = conn.execute(
                """
                SELECT message_uid AS messageId, role, content, created_at AS createdAt
                FROM agent_long_conversation_messages
                WHERE conversation_id = ?
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (row["id"], message_limit, message_offset),
            ).fetchall()
            return self._long_summary(row), messages, int(row["message_count"])

    def append_long_exchange(
        self,
        user_id: int,
        conversation_uid: str,
        request_id: str,
        user_message: str,
        assistant_message: str,
    ) -> bool | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conversation = conn.execute(
                """
                SELECT id FROM agent_long_conversations
                WHERE user_id = ?
                  AND (conversation_uid = ? OR source_session_uid = ?)
                """,
                (user_id, conversation_uid, conversation_uid),
            ).fetchone()
            if not conversation:
                return None
            existing = conn.execute(
                """
                SELECT 1 FROM agent_long_conversation_messages
                WHERE conversation_id = ? AND request_id = ? AND role = 'assistant'
                """,
                (conversation["id"], request_id),
            ).fetchone()
            if existing:
                return False
            conn.executemany(
                """
                INSERT INTO agent_long_conversation_messages(
                    message_uid, conversation_id, role, content, request_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    (
                        f"lgm_{uuid4().hex}",
                        conversation["id"],
                        "user",
                        user_message,
                        request_id,
                    ),
                    (
                        f"lgm_{uuid4().hex}",
                        conversation["id"],
                        "assistant",
                        assistant_message,
                        request_id,
                    ),
                ),
            )
            conn.execute(
                """
                UPDATE agent_long_conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation["id"],),
            )
            return True

    def has_long_source(self, user_id: int, session_uid: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM agent_long_conversations
                WHERE user_id = ? AND source_session_uid = ?
                LIMIT 1
                """,
                (user_id, session_uid),
            ).fetchone()
            return bool(row)

    def update_long(
        self,
        user_id: int,
        conversation_uid: str,
        *,
        title: str | None,
        pinned_at: str | None | object,
    ) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conversation = conn.execute(
                """
                SELECT id FROM agent_long_conversations
                WHERE user_id = ? AND conversation_uid = ?
                """,
                (user_id, conversation_uid),
            ).fetchone()
            if not conversation:
                return None
            assignments = ["updated_at = CURRENT_TIMESTAMP"]
            values: list[object] = []
            if title is not None:
                assignments.append("title = ?")
                values.append(title)
            if pinned_at is not _UNCHANGED:
                assignments.append("pinned_at = ?")
                values.append(pinned_at)
            values.append(conversation["id"])
            conn.execute(
                f"UPDATE agent_long_conversations SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
            row = conn.execute(
                """
                SELECT c.*, COUNT(m.id) AS message_count
                FROM agent_long_conversations c
                LEFT JOIN agent_long_conversation_messages m
                  ON m.conversation_id = c.id
                WHERE c.id = ?
                GROUP BY c.id
                """,
                (conversation["id"],),
            ).fetchone()
            return self._long_summary(row)

    def delete_long(self, user_id: int, conversation_uid: str) -> bool:
        with self._connect() as conn:
            result = conn.execute(
                """
                DELETE FROM agent_long_conversations
                WHERE user_id = ? AND conversation_uid = ?
                """,
                (user_id, conversation_uid),
            )
            return bool(result.rowcount)


class AgentSessionService:
    def __init__(
        self,
        store: AgentSessionStore,
        retention_days: int = AGENT_SESSION_RETENTION_DAYS,
    ):
        self.store = store
        self.retention_days = retention_days

    def _expires_at(self) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.retention_days
        )
        return expires_at.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _not_found() -> AgentSessionError:
        return AgentSessionError("AGENT_SESSION_NOT_FOUND", "会话不存在", 404)

    @staticmethod
    def _long_not_found() -> AgentSessionError:
        return AgentSessionError(
            "AGENT_LONG_CONVERSATION_NOT_FOUND",
            "长期对话不存在",
            404,
        )

    def create(self, user_id: int, title: str | None) -> dict:
        clean_title = (title or "").strip() or "新对话"
        session = self.store.create(
            user_id,
            f"ags_{uuid4().hex}",
            clean_title,
            self._expires_at(),
        )
        if session is None:
            raise AgentSessionError(
                "AGENT_SESSION_UNSTARTED_EXISTS",
                "请先在当前对话中完成一次问答",
                409,
            )
        return {
            "session": session
        }

    def ensure_draft(self, user_id: int) -> dict:
        return {
            "session": self.store.ensure_draft(
                user_id,
                f"ags_{uuid4().hex}",
                "新对话",
                self._expires_at(),
            )
        }

    def list(self, user_id: int, limit: int, offset: int) -> dict:
        items, total = self.store.list(user_id, limit, offset)
        return {
            "items": items,
            "meta": {
                "limit": limit,
                "offset": offset,
                "totalCount": total,
                "hasNext": offset + len(items) < total,
                "contractVersion": 1,
            },
        }

    def get(
        self,
        user_id: int,
        session_uid: str,
        message_limit: int,
        message_offset: int,
    ) -> dict:
        result = self.store.get(
            user_id,
            session_uid,
            message_limit,
            message_offset,
        )
        if not result:
            raise self._not_found()
        session, messages, total = result
        return {
            "session": session,
            "messages": messages,
            "meta": {
                "limit": message_limit,
                "offset": message_offset,
                "totalCount": total,
                "hasNext": message_offset + len(messages) < total,
                "contractVersion": 1,
            },
        }

    def require_owned(self, user_id: int, session_uid: str) -> None:
        if session_uid.startswith("agl_"):
            if not self.store.get_long(user_id, session_uid, 1, 0):
                raise self._long_not_found()
            return
        if self.store.get(user_id, session_uid, 1, 0):
            return
        if not self.store.has_long_source(user_id, session_uid):
            raise self._not_found()

    def context(
        self,
        user_id: int,
        session_uid: str,
        *,
        limit: int = 12,
        max_chars: int = 24_000,
    ) -> tuple[AgentHistoryMessage, ...]:
        if limit < 1 or max_chars < 1:
            raise ValueError("history limits must be positive")
        # Read a bounded wider window so completed older exchanges can be
        # represented by compact final reports instead of disappearing or
        # sending their full transcripts back to the model.
        rows = self.store.context(user_id, session_uid, min(max(limit * 3, limit), 48))
        if rows is None:
            if session_uid.startswith("agl_"):
                raise self._long_not_found()
            raise self._not_found()
        history = compact_conversation_history(
            tuple(AgentHistoryMessage.model_validate(row) for row in rows),
            recent_exchanges=2,
            max_reports=min(4, max(0, limit - 4)),
        )
        total_chars = 0
        selected: list[AgentHistoryMessage] = []
        for message in reversed(history):
            next_total = total_chars + len(message.content)
            if next_total > max_chars:
                break
            selected.append(message)
            total_chars = next_total
        return tuple(reversed(selected))

    def append_exchange(
        self,
        user_id: int,
        session_uid: str,
        request_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        if session_uid.startswith("agl_"):
            created = self.store.append_long_exchange(
                user_id,
                session_uid,
                request_id,
                user_message.strip(),
                assistant_message.strip(),
            )
            if created is None:
                raise self._long_not_found()
            return
        created = self.store.append_exchange(
            user_id,
            session_uid,
            request_id,
            user_message.strip(),
            assistant_message.strip(),
            self._expires_at(),
        )
        if created is None:
            created = self.store.append_long_exchange(
                user_id,
                session_uid,
                request_id,
                user_message.strip(),
                assistant_message.strip(),
            )
            if created is None:
                raise self._not_found()

    def delete(self, user_id: int, session_uid: str) -> None:
        if not self.store.delete(user_id, session_uid):
            raise self._not_found()

    def update(
        self,
        user_id: int,
        session_uid: str,
        *,
        title: str | None,
        pinned: bool | None,
    ) -> dict:
        clean_title = None
        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise AgentSessionError(
                    "AGENT_SESSION_TITLE_INVALID",
                    "对话标题不能为空",
                    422,
                )
        pinned_at: str | None | object = _UNCHANGED
        if pinned is True:
            pinned_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )
        elif pinned is False:
            pinned_at = None
        session = self.store.update(
            user_id,
            session_uid,
            title=clean_title,
            pinned_at=pinned_at,
        )
        if session is None:
            raise self._not_found()
        return {"session": session}

    def upgrade(self, user_id: int, session_uid: str) -> dict:
        status, conversation = self.store.upgrade(
            user_id,
            session_uid,
            f"agl_{uuid4().hex}",
            LONG_CONVERSATION_LIMIT,
        )
        if status == "missing":
            raise self._not_found()
        if status == "unstarted":
            raise AgentSessionError(
                "AGENT_SESSION_NOT_STARTED",
                "完成一次问答后才能升级为长期对话",
                409,
            )
        if status == "limit":
            raise AgentSessionError(
                "AGENT_LONG_CONVERSATION_LIMIT_REACHED",
                "每个用户最多保存三个长期对话",
                409,
            )
        return {"conversation": conversation}

    def list_long(self, user_id: int, limit: int, offset: int) -> dict:
        items, total = self.store.list_long(user_id, limit, offset)
        return {
            "items": items,
            "meta": {
                "limit": limit,
                "offset": offset,
                "totalCount": total,
                "hasNext": offset + len(items) < total,
                "contractVersion": 1,
            },
        }

    def get_long(
        self,
        user_id: int,
        conversation_uid: str,
        message_limit: int,
        message_offset: int,
    ) -> dict:
        result = self.store.get_long(
            user_id,
            conversation_uid,
            message_limit,
            message_offset,
        )
        if not result:
            raise self._long_not_found()
        conversation, messages, total = result
        return {
            "conversation": conversation,
            "messages": messages,
            "meta": {
                "limit": message_limit,
                "offset": message_offset,
                "totalCount": total,
                "hasNext": message_offset + len(messages) < total,
                "contractVersion": 1,
            },
        }

    def update_long(
        self,
        user_id: int,
        conversation_uid: str,
        *,
        title: str | None,
        pinned: bool | None,
    ) -> dict:
        clean_title = None
        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise AgentSessionError(
                    "AGENT_SESSION_TITLE_INVALID",
                    "对话标题不能为空",
                    422,
                )
        pinned_at: str | None | object = _UNCHANGED
        if pinned is True:
            pinned_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )
        elif pinned is False:
            pinned_at = None
        conversation = self.store.update_long(
            user_id,
            conversation_uid,
            title=clean_title,
            pinned_at=pinned_at,
        )
        if conversation is None:
            raise self._long_not_found()
        return {"conversation": conversation}

    def delete_long(self, user_id: int, conversation_uid: str) -> None:
        if not self.store.delete_long(user_id, conversation_uid):
            raise self._long_not_found()


@lru_cache(maxsize=1)
def get_agent_session_service() -> AgentSessionService:
    return AgentSessionService(AgentSessionStore())
