import asyncio
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.agent.sessions import AgentSessionError, AgentSessionService, AgentSessionStore
from app.agent.schemas import AgentChatRequest, AgentHistoryMessage, AgentStructuredResponse
from app.db.database import apply_migrations, dict_factory


BASE_DIR = Path(__file__).resolve().parents[1]


class AgentSessionServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "agent-sessions.sqlite3"
        with closing(sqlite3.connect(self.database_path)) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(
                (BASE_DIR / "database" / "schema.sql").read_text(encoding="utf-8")
            )
            apply_migrations(conn, BASE_DIR / "database" / "migrations")
            conn.execute(
                "INSERT INTO user_accounts(user_uid, username) VALUES ('user_alice', 'alice')"
            )
            conn.execute(
                "INSERT INTO user_accounts(user_uid, username) VALUES ('user_bob', 'bob')"
            )
            self.alice_id = conn.execute(
                "SELECT id FROM user_accounts WHERE user_uid = 'user_alice'"
            ).fetchone()[0]
            self.bob_id = conn.execute(
                "SELECT id FROM user_accounts WHERE user_uid = 'user_bob'"
            ).fetchone()[0]
            conn.commit()
        self.service = AgentSessionService(
            AgentSessionStore(self._connection)
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _connection(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _completed_session(self, index: int) -> dict:
        session = self.service.create(self.alice_id, None)["session"]
        self.service.append_exchange(
            self.alice_id,
            session["sessionId"],
            f"request-long-{index}",
            f"长期问题 {index}",
            f"长期回答 {index}",
        )
        return session

    def test_create_append_page_and_delete_minimal_history(self):
        first = self.service.create(self.alice_id, None)["session"]
        with self.assertRaises(AgentSessionError) as unstarted:
            self.service.create(self.alice_id, "不应创建")
        self.assertEqual(
            "AGENT_SESSION_UNSTARTED_EXISTS",
            unstarted.exception.code,
        )
        self.assertEqual(409, unstarted.exception.status_code)

        self.service.append_exchange(
            self.alice_id,
            first["sessionId"],
            "request-1",
            "  请推荐一个免费的学习工具  ",
            "可以先查看站内的免费工具清单。",
        )
        # A retried request ID must not duplicate either side of the exchange.
        self.service.append_exchange(
            self.alice_id,
            first["sessionId"],
            "request-1",
            "不应重复保存",
            "不应重复保存",
        )
        second = self.service.create(self.alice_id, "第二个会话")["session"]
        self.service.append_exchange(
            self.alice_id,
            second["sessionId"],
            "request-2",
            "第二个问题",
            "第二个回答",
        )
        third = self.service.create(self.alice_id, "第三个会话")["session"]

        page = self.service.list(self.alice_id, limit=2, offset=0)
        self.assertEqual(page["meta"]["totalCount"], 3)
        self.assertTrue(page["meta"]["hasNext"])
        self.assertEqual(len(page["items"]), 2)
        self.assertIn("expiresAt", page["items"][0])
        self.assertIn(second["sessionId"], {item["sessionId"] for item in page["items"]})
        self.assertIn(third["sessionId"], {item["sessionId"] for item in page["items"]})

        detail = self.service.get(
            self.alice_id,
            first["sessionId"],
            message_limit=1,
            message_offset=0,
        )
        self.assertEqual(detail["session"]["title"], "请推荐一个免费的学习工具")
        self.assertEqual(detail["meta"]["totalCount"], 2)
        self.assertTrue(detail["meta"]["hasNext"])
        self.assertEqual(detail["messages"][0]["role"], "user")
        self.assertEqual(detail["messages"][0]["content"], "请推荐一个免费的学习工具")
        self.assertNotIn("requestId", detail["messages"][0])

        with closing(self._connection()) as conn:
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(agent_chat_messages)"
                ).fetchall()
            }
            self.assertFalse(
                columns.intersection(
                    {"provider_payload", "system_prompt", "api_key", "user_context"}
                )
            )
            conn.execute(
                """
                UPDATE agent_chat_sessions
                SET expires_at = '2000-01-01 00:00:00'
                WHERE session_uid = ?
                """,
                (third["sessionId"],),
            )
            conn.commit()

        after_expiry = self.service.list(self.alice_id, limit=10, offset=0)
        self.assertEqual(after_expiry["meta"]["totalCount"], 2)
        self.assertNotIn(
            third["sessionId"],
            {item["sessionId"] for item in after_expiry["items"]},
        )

        self.service.delete(self.alice_id, first["sessionId"])
        with closing(self._connection()) as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) AS count FROM agent_chat_messages"
            ).fetchone()
            self.assertEqual(remaining["count"], 2)

    def test_ensure_draft_reuses_one_empty_session_and_creates_after_use(self):
        first = self.service.ensure_draft(self.alice_id)["session"]
        reused = self.service.ensure_draft(self.alice_id)["session"]
        self.assertEqual(first["sessionId"], reused["sessionId"])

        self.service.append_exchange(
            self.alice_id,
            first["sessionId"],
            "request-draft-1",
            "开始使用草稿",
            "草稿已成为正式会话",
        )
        replacement = self.service.ensure_draft(self.alice_id)["session"]
        self.assertNotEqual(first["sessionId"], replacement["sessionId"])
        self.assertEqual(0, replacement["messageCount"])

        draft_ids = {
            item["sessionId"]
            for item in self.service.list(self.alice_id, 20, 0)["items"]
            if item["messageCount"] == 0
        }
        self.assertEqual({replacement["sessionId"]}, draft_ids)

    def test_cross_user_access_is_indistinguishable_from_missing(self):
        session = self.service.create(self.alice_id, None)["session"]

        for operation in (
            lambda: self.service.get(self.bob_id, session["sessionId"], 50, 0),
            lambda: self.service.require_owned(self.bob_id, session["sessionId"]),
            lambda: self.service.context(self.bob_id, session["sessionId"]),
            lambda: self.service.append_exchange(
                self.bob_id,
                session["sessionId"],
                "request-cross-user",
                "越权问题",
                "越权回答",
            ),
            lambda: self.service.delete(self.bob_id, session["sessionId"]),
        ):
            with self.assertRaises(AgentSessionError) as raised:
                operation()
            self.assertEqual(raised.exception.code, "AGENT_SESSION_NOT_FOUND")
            self.assertEqual(raised.exception.status_code, 404)

        self.assertEqual(
            self.service.get(self.alice_id, session["sessionId"], 50, 0)[
                "session"
            ]["messageCount"],
            0,
        )

    def test_context_returns_latest_complete_messages_in_chronological_order(self):
        empty = self.service.create(self.alice_id, None)["session"]
        self.assertEqual((), self.service.context(self.alice_id, empty["sessionId"]))

        for index in range(8):
            self.service.append_exchange(
                self.alice_id,
                empty["sessionId"],
                f"request-context-{index}",
                f"user-{index}",
                f"assistant-{index}",
            )

        history = self.service.context(self.alice_id, empty["sessionId"])
        self.assertEqual(8, len(history))
        self.assertEqual(
            [
                "[当前对话内的已完成任务记录]",
                "[当前对话内的已完成任务记录]",
            ],
            [message.content.splitlines()[0] for message in history[:2]],
        )
        self.assertEqual(
            ["user-7", "assistant-7"],
            [message.content for message in history[-2:]],
        )
        self.assertTrue(
            all(message.role in {"user", "assistant"} for message in history)
        )
        self.assertTrue(all(message.role == "assistant" for message in history[:4]))
        self.assertIn("用户目标：user-2", history[0].content)
        self.assertIn("最终结果：assistant-2", history[0].content)

    def test_conversation_context_never_includes_another_conversation(self):
        first = self.service.create(self.alice_id, None)["session"]
        self.service.append_exchange(
            self.alice_id,
            first["sessionId"],
            "request-isolation-a",
            "只属于对话 A 的临时口令：青松",
            "已在对话 A 中收到",
        )
        second = self.service.create(self.alice_id, None)["session"]
        self.service.append_exchange(
            self.alice_id,
            second["sessionId"],
            "request-isolation-b",
            "只属于对话 B 的问题",
            "已在对话 B 中回答",
        )

        first_history = self.service.context(self.alice_id, first["sessionId"])
        second_history = self.service.context(self.alice_id, second["sessionId"])
        self.assertIn("青松", " ".join(item.content for item in first_history))
        self.assertNotIn("青松", " ".join(item.content for item in second_history))

        upgraded = self.service.upgrade(
            self.alice_id,
            first["sessionId"],
        )["conversation"]
        long_history = self.service.context(
            self.alice_id,
            upgraded["conversationId"],
        )
        self.assertIn("青松", " ".join(item.content for item in long_history))
        self.assertNotIn("对话 B", " ".join(item.content for item in long_history))

    def test_context_trims_only_whole_messages_from_the_oldest_end(self):
        session = self.service.create(self.alice_id, None)["session"]
        for index in range(3):
            self.service.append_exchange(
                self.alice_id,
                session["sessionId"],
                f"request-budget-{index}",
                str(index) + ("u" * 2999),
                str(index) + ("a" * 2999),
            )

        history = self.service.context(
            self.alice_id,
            session["sessionId"],
            max_chars=12_000,
        )

        self.assertEqual(4, len(history))
        self.assertEqual(["1", "1", "2", "2"], [item.content[0] for item in history])
        self.assertEqual(12_000, sum(len(item.content) for item in history))
        self.assertTrue(all(len(item.content) == 3000 for item in history))

    def test_context_compaction_is_session_scoped_and_excludes_runtime_artifacts(self):
        first = self.service.create(self.alice_id, None)["session"]
        for index in range(5):
            self.service.append_exchange(
                self.alice_id,
                first["sessionId"],
                f"request-report-{index}",
                f"对话 A 任务 {index}",
                f"对话 A 最终成果 {index}",
            )
        second = self.service.create(self.alice_id, None)["session"]
        self.service.append_exchange(
            self.alice_id,
            second["sessionId"],
            "request-report-b",
            "对话 B 私有目标",
            "对话 B 最终成果",
        )

        history = self.service.context(self.alice_id, first["sessionId"])
        joined = "\n".join(item.content for item in history)

        self.assertIn("[当前对话内的已完成任务记录]", joined)
        self.assertIn("对话 A 最终成果 2", joined)
        self.assertNotIn("对话 B", joined)
        self.assertNotIn("Traceback", joined)
        self.assertNotIn("diagnosticNote", joined)
        self.assertNotIn("toolEvidence", joined)

    def test_rename_and_multiple_pin_order_is_user_owned(self):
        first = self.service.create(self.alice_id, None)["session"]
        self.service.append_exchange(
            self.alice_id,
            first["sessionId"],
            "request-pin-1",
            "第一个问题",
            "第一个回答",
        )
        second = self.service.create(self.alice_id, None)["session"]
        self.service.append_exchange(
            self.alice_id,
            second["sessionId"],
            "request-pin-2",
            "第二个问题",
            "第二个回答",
        )

        renamed = self.service.update(
            self.alice_id,
            first["sessionId"],
            title="  我的学习计划  ",
            pinned=True,
        )["session"]
        self.assertEqual("我的学习计划", renamed["title"])
        self.assertTrue(renamed["pinned"])
        self.assertIsNotNone(renamed["pinnedAt"])

        later_pin = self.service.update(
            self.alice_id,
            second["sessionId"],
            title=None,
            pinned=True,
        )["session"]
        self.assertTrue(later_pin["pinned"])
        ordered = self.service.list(self.alice_id, 20, 0)["items"]
        self.assertEqual(
            [second["sessionId"], first["sessionId"]],
            [item["sessionId"] for item in ordered],
        )

        unpinned = self.service.update(
            self.alice_id,
            second["sessionId"],
            title=None,
            pinned=False,
        )["session"]
        self.assertFalse(unpinned["pinned"])
        self.assertEqual(
            first["sessionId"],
            self.service.list(self.alice_id, 20, 0)["items"][0]["sessionId"],
        )

        with self.assertRaises(AgentSessionError) as cross_user:
            self.service.update(
                self.bob_id,
                first["sessionId"],
                title="越权修改",
                pinned=True,
            )
        self.assertEqual("AGENT_SESSION_NOT_FOUND", cross_user.exception.code)

    def test_upgrade_moves_completed_session_and_remains_writable(self):
        session = self._completed_session(1)
        upgraded = self.service.upgrade(
            self.alice_id,
            session["sessionId"],
        )["conversation"]
        self.assertTrue(upgraded["conversationId"].startswith("agl_"))
        self.assertEqual(2, upgraded["messageCount"])
        self.assertEqual("长期问题 1", upgraded["title"])

        with self.assertRaises(AgentSessionError) as moved:
            self.service.get(self.alice_id, session["sessionId"], 50, 0)
        self.assertEqual("AGENT_SESSION_NOT_FOUND", moved.exception.code)
        self.assertEqual(0, self.service.list(self.alice_id, 20, 0)["meta"]["totalCount"])
        self.assertEqual(
            upgraded["conversationId"],
            self.service.list_long(self.alice_id, 20, 0)["items"][0][
                "conversationId"
            ],
        )

        # A retry uses the source short-session UID as the idempotency key.
        retried = self.service.upgrade(
            self.alice_id,
            session["sessionId"],
        )["conversation"]
        self.assertEqual(upgraded["conversationId"], retried["conversationId"])

        # A request that started before the move may still carry the old short ID.
        self.service.require_owned(self.alice_id, session["sessionId"])
        self.service.append_exchange(
            self.alice_id,
            session["sessionId"],
            "request-upgrade-race",
            "升级同时完成的问题",
            "升级同时完成的回答",
        )
        self.service.require_owned(self.alice_id, upgraded["conversationId"])
        self.service.append_exchange(
            self.alice_id,
            upgraded["conversationId"],
            "request-long-continued",
            "继续提问",
            "继续回答",
        )
        detail = self.service.get_long(
            self.alice_id,
            upgraded["conversationId"],
            100,
            0,
        )
        self.assertEqual(6, detail["meta"]["totalCount"])
        self.assertEqual("继续回答", detail["messages"][-1]["content"])

        renamed = self.service.update_long(
            self.alice_id,
            upgraded["conversationId"],
            title="长期学习计划",
            pinned=True,
        )["conversation"]
        self.assertEqual("长期学习计划", renamed["title"])
        self.assertTrue(renamed["pinned"])

    def test_long_conversation_limit_unstarted_and_user_isolation(self):
        unstarted = self.service.create(self.alice_id, None)["session"]
        with self.assertRaises(AgentSessionError) as not_started:
            self.service.upgrade(self.alice_id, unstarted["sessionId"])
        self.assertEqual("AGENT_SESSION_NOT_STARTED", not_started.exception.code)
        self.service.delete(self.alice_id, unstarted["sessionId"])

        upgraded_ids = []
        for index in range(3):
            session = self._completed_session(index + 10)
            upgraded_ids.append(
                self.service.upgrade(
                    self.alice_id,
                    session["sessionId"],
                )["conversation"]["conversationId"]
            )
        fourth = self._completed_session(20)
        with self.assertRaises(AgentSessionError) as limited:
            self.service.upgrade(self.alice_id, fourth["sessionId"])
        self.assertEqual(
            "AGENT_LONG_CONVERSATION_LIMIT_REACHED",
            limited.exception.code,
        )
        self.assertEqual(
            3,
            self.service.list_long(self.alice_id, 20, 0)["meta"]["totalCount"],
        )
        # Failed upgrades leave the original short conversation untouched.
        self.assertEqual(
            2,
            self.service.get(
                self.alice_id,
                fourth["sessionId"],
                50,
                0,
            )["meta"]["totalCount"],
        )

        with self.assertRaises(AgentSessionError) as cross_user:
            self.service.get_long(self.bob_id, upgraded_ids[0], 50, 0)
        self.assertEqual(
            "AGENT_LONG_CONVERSATION_NOT_FOUND",
            cross_user.exception.code,
        )
        self.service.delete_long(self.alice_id, upgraded_ids[0])
        with self.assertRaises(AgentSessionError):
            self.service.get_long(self.alice_id, upgraded_ids[0], 50, 0)

    def test_session_routes_have_an_independent_default_off_switch(self):
        from app.api.v1.routers.agent import _require_sessions_enabled

        with patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", False):
            with self.assertRaises(HTTPException) as raised:
                _require_sessions_enabled()
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail["code"],
            "AGENT_SESSIONS_DISABLED",
        )


class AgentSessionRouterIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_successful_session_request_appends_one_exchange(self):
        from app.api.v1.routers.agent import _run_agent_request

        class SessionService:
            def __init__(self):
                self.required = []
                self.appended = []

            def require_owned(self, user_id, session_id):
                self.required.append((user_id, session_id))

            def context(self, _user_id, _session_id):
                return ()

            def append_exchange(self, *args):
                self.appended.append(args)

        class Orchestrator:
            async def respond(self, *_args, **_kwargs):
                return AgentStructuredResponse(answer="最终回答")

        session_service = SessionService()
        payload = AgentChatRequest(
            message="用户问题",
            sessionId="ags_12345678",
        )
        with (
            patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True),
            patch(
                "app.api.v1.routers.agent.get_agent_session_service",
                return_value=session_service,
            ),
        ):
            result = await _run_agent_request(
                payload,
                {"id": 7},
                Orchestrator(),
                "request-success",
            )

        self.assertEqual(result.answer, "最终回答")
        self.assertEqual(session_service.required, [(7, "ags_12345678")])
        self.assertEqual(
            session_service.appended,
            [
                (
                    7,
                    "ags_12345678",
                    "request-success",
                    "用户问题",
                    "最终回答",
                )
            ],
        )

    async def test_history_is_loaded_after_ownership_and_before_generation(self):
        from app.api.v1.routers.agent import _run_agent_request

        calls = []
        history = (
            AgentHistoryMessage(role="user", content="earlier question"),
            AgentHistoryMessage(role="assistant", content="earlier answer"),
        )

        class SessionService:
            def __init__(self):
                self.history = history

            def require_owned(self, _user_id, _session_id):
                calls.append("require_owned")

            def context(self, _user_id, _session_id):
                calls.append("context")
                return self.history

            def append_exchange(
                self,
                _user_id,
                _session_id,
                _request_id,
                user_message,
                assistant_message,
            ):
                calls.append("append_exchange")
                self.history += (
                    AgentHistoryMessage(role="user", content=user_message),
                    AgentHistoryMessage(role="assistant", content=assistant_message),
                )

        class Orchestrator:
            async def respond(self, *_args, **kwargs):
                calls.append("respond")
                self.history = kwargs["history"]
                return AgentStructuredResponse(answer="final answer")

        session_service = SessionService()
        orchestrator = Orchestrator()
        payload = AgentChatRequest(
            message="current question",
            sessionId="ags_12345678",
        )
        with (
            patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True),
            patch(
                "app.api.v1.routers.agent.get_agent_session_service",
                return_value=session_service,
            ),
        ):
            await _run_agent_request(
                payload,
                {"id": 7},
                orchestrator,
                "request-history-order",
            )

        self.assertEqual(history, orchestrator.history)
        self.assertEqual(
            ["require_owned", "context", "respond", "append_exchange", "context"],
            calls,
        )

    async def test_cancelled_session_request_does_not_append(self):
        from app.api.v1.routers.agent import _run_agent_request

        class SessionService:
            def __init__(self):
                self.appended = []

            def require_owned(self, _user_id, _session_id):
                return None

            def context(self, _user_id, _session_id):
                return ()

            def append_exchange(self, *args):
                self.appended.append(args)

        class Orchestrator:
            async def respond(self, *_args, **_kwargs):
                await asyncio.Event().wait()

        session_service = SessionService()
        with (
            patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True),
            patch(
                "app.api.v1.routers.agent.get_agent_session_service",
                return_value=session_service,
            ),
        ):
            task = asyncio.create_task(
                _run_agent_request(
                    AgentChatRequest(
                        message="会被取消的问题",
                        sessionId="ags_12345678",
                    ),
                    {"id": 7},
                    Orchestrator(),
                    "request-cancelled",
                )
            )
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertEqual(session_service.appended, [])


if __name__ == "__main__":
    unittest.main()
