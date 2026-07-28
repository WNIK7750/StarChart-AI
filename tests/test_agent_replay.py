import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from app.agent.replay import (
    AgentReplayConflict,
    AgentReplaySingleFlight,
    AgentResponseReplayCache,
    request_fingerprint,
)
from app.agent.schemas import AgentChatRequest, AgentHistoryMessage, AgentStructuredResponse


def response(answer: str = "已完成") -> AgentStructuredResponse:
    return AgentStructuredResponse(answer=answer)


class AgentResponseReplayCacheTests(unittest.TestCase):
    def test_cache_returns_defensive_copy_and_expires(self):
        now = [10.0]
        cache = AgentResponseReplayCache(
            ttl_seconds=30,
            max_entries=4,
            clock=lambda: now[0],
        )
        payload = AgentChatRequest(message="介绍 RAG")
        fingerprint = request_fingerprint(payload)
        original = response()

        cache.put(7, "request-1", fingerprint, original)
        replayed = cache.get(7, "request-1", fingerprint)

        self.assertEqual(original, replayed)
        self.assertIsNot(original, replayed)
        replayed.answer = "被调用方修改"
        self.assertEqual("已完成", cache.get(7, "request-1", fingerprint).answer)

        now[0] = 40.0
        self.assertIsNone(cache.get(7, "request-1", fingerprint))

    def test_cache_rejects_request_id_reuse_with_different_payload(self):
        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        first = request_fingerprint(AgentChatRequest(message="第一个问题"))
        second = request_fingerprint(AgentChatRequest(message="另一个问题"))
        cache.put(7, "request-1", first, response())

        with self.assertRaises(AgentReplayConflict):
            cache.get(7, "request-1", second)
        with self.assertRaises(AgentReplayConflict):
            cache.put(7, "request-1", second, response("另一个回答"))

    def test_fingerprint_changes_when_resolved_session_history_changes(self):
        payload = AgentChatRequest(message="same current question")
        first = request_fingerprint(
            payload,
            history=(AgentHistoryMessage(role="user", content="first history"),),
        )
        second = request_fingerprint(
            payload,
            history=(AgentHistoryMessage(role="user", content="changed history"),),
        )
        self.assertNotEqual(first, second)

    def test_cache_evicts_least_recently_used_entry(self):
        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=2)
        fingerprints = {}
        for index in range(3):
            payload = AgentChatRequest(message=f"问题 {index}")
            fingerprints[index] = request_fingerprint(payload)
            cache.put(7, f"request-{index}", fingerprints[index], response(str(index)))

        self.assertIsNone(cache.get(7, "request-0", fingerprints[0]))
        self.assertEqual("1", cache.get(7, "request-1", fingerprints[1]).answer)
        self.assertEqual("2", cache.get(7, "request-2", fingerprints[2]).answer)


class AgentReplaySingleFlightTests(unittest.IsolatedAsyncioTestCase):
    async def test_different_keys_run_concurrently_and_completed_keys_are_released(self):
        singleflight = AgentReplaySingleFlight()
        both_acquired = asyncio.Event()
        release = asyncio.Event()
        acquired = 0

        async def use_slot(request_id):
            nonlocal acquired
            async with singleflight.slot(7, request_id):
                acquired += 1
                if acquired == 2:
                    both_acquired.set()
                await release.wait()

        first = asyncio.create_task(use_slot("request-one"))
        second = asyncio.create_task(use_slot("request-two"))
        await asyncio.wait_for(both_acquired.wait(), timeout=1)
        release.set()
        await asyncio.gather(first, second)

        self.assertEqual({}, singleflight._entries)


class AgentResponseReplayRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_identical_session_requests_generate_append_and_cache_once(self):
        from app.api.v1.routers.agent import _run_agent_request

        class CountingCache(AgentResponseReplayCache):
            def __init__(self):
                super().__init__(ttl_seconds=30, max_entries=4)
                self.put_count = 0

            def put(self, *args):
                self.put_count += 1
                return super().put(*args)

        class SessionService:
            def __init__(self):
                self.history = ()
                self.appended = 0

            def require_owned(self, _user_id, _session_id):
                return None

            def context(self, _user_id, _session_id):
                return self.history

            def append_exchange(
                self,
                _user_id,
                _session_id,
                _request_id,
                user_message,
                assistant_message,
            ):
                self.appended += 1
                self.history += (
                    AgentHistoryMessage(role="user", content=user_message),
                    AgentHistoryMessage(role="assistant", content=assistant_message),
                )

        cache = CountingCache()
        sessions = SessionService()
        started = asyncio.Event()
        release = asyncio.Event()
        generated = 0

        async def respond(*_args, **_kwargs):
            nonlocal generated
            generated += 1
            started.set()
            await release.wait()
            return response(f"answer-{generated}")

        orchestrator = Mock()
        orchestrator.respond = respond
        payload = AgentChatRequest(
            message="same question",
            sessionId="ags_12345678",
        )
        with (
            patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True),
            patch(
                "app.api.v1.routers.agent.get_agent_session_service",
                return_value=sessions,
            ),
            patch(
                "app.api.v1.routers.agent.get_agent_response_replay_cache",
                return_value=cache,
            ),
        ):
            first_task = asyncio.create_task(
                _run_agent_request(payload, {"id": 7}, orchestrator, "request-concurrent")
            )
            await started.wait()
            second_task = asyncio.create_task(
                _run_agent_request(payload, {"id": 7}, orchestrator, "request-concurrent")
            )
            await asyncio.sleep(0)
            release.set()
            first, second = await asyncio.gather(first_task, second_task)

        self.assertEqual(first, second)
        self.assertEqual(1, generated)
        self.assertEqual(1, sessions.appended)
        self.assertEqual(1, cache.put_count)

    async def test_concurrent_different_payload_with_same_request_id_returns_conflict(self):
        from app.api.v1.routers.agent import _run_agent_request

        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        started = asyncio.Event()
        release = asyncio.Event()
        generated = 0

        async def respond(*_args, **_kwargs):
            nonlocal generated
            generated += 1
            started.set()
            await release.wait()
            return response("first answer")

        orchestrator = Mock()
        orchestrator.respond = respond
        with patch(
            "app.api.v1.routers.agent.get_agent_response_replay_cache",
            return_value=cache,
        ):
            first_task = asyncio.create_task(
                _run_agent_request(
                    AgentChatRequest(message="first question"),
                    {"id": 7},
                    orchestrator,
                    "request-conflict",
                )
            )
            await started.wait()
            conflicting_task = asyncio.create_task(
                _run_agent_request(
                    AgentChatRequest(message="different question"),
                    {"id": 7},
                    orchestrator,
                    "request-conflict",
                )
            )
            await asyncio.sleep(0)
            release.set()
            first = await first_task
            with self.assertRaises(HTTPException) as conflict:
                await conflicting_task

        self.assertEqual("first answer", first.answer)
        self.assertEqual(409, conflict.exception.status_code)
        self.assertEqual(1, generated)

    async def test_cancellation_during_session_finalization_cannot_leave_append_without_replay(self):
        from app.api.v1.routers.agent import _run_agent_request

        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        post_append_context_started = asyncio.Event()
        finish_context = asyncio.Event()

        class SessionService:
            def __init__(self):
                self.history = ()
                self.appended = 0
                self.context_calls = 0

            def require_owned(self, _user_id, _session_id):
                return None

            def context(self, _user_id, _session_id):
                self.context_calls += 1
                return self.history

            def append_exchange(
                self,
                _user_id,
                _session_id,
                _request_id,
                user_message,
                assistant_message,
            ):
                self.appended += 1
                self.history += (
                    AgentHistoryMessage(role="user", content=user_message),
                    AgentHistoryMessage(role="assistant", content=assistant_message),
                )

        sessions = SessionService()
        async def controlled_threadpool(function, *args):
            if function == sessions.context and sessions.context_calls == 1:
                post_append_context_started.set()
                await finish_context.wait()
            return function(*args)

        orchestrator = Mock()
        orchestrator.respond = AsyncMock(return_value=response("finalized answer"))
        payload = AgentChatRequest(
            message="question finalized under cancellation",
            sessionId="ags_12345678",
        )
        with (
            patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True),
            patch(
                "app.api.v1.routers.agent.get_agent_session_service",
                return_value=sessions,
            ),
            patch(
                "app.api.v1.routers.agent.get_agent_response_replay_cache",
                return_value=cache,
            ),
            patch(
                "app.api.v1.routers.agent.run_in_threadpool",
                side_effect=controlled_threadpool,
            ),
        ):
            task = asyncio.create_task(
                _run_agent_request(payload, {"id": 7}, orchestrator, "request-cancel-finalize")
            )
            await post_append_context_started.wait()
            task.cancel()
            finish_context.set()
            with self.assertRaises(asyncio.CancelledError):
                await task

        fingerprint = request_fingerprint(payload, history=sessions.history)
        replayed = cache.get(7, "request-cancel-finalize", fingerprint)
        self.assertEqual(1, sessions.appended)
        self.assertIsNotNone(replayed)
        self.assertEqual("finalized answer", replayed.answer)

    async def test_session_retry_replays_once_but_later_history_change_conflicts(self):
        from app.api.v1.routers.agent import _run_agent_request

        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        orchestrator = Mock()
        orchestrator.respond = AsyncMock(return_value=response("session answer"))
        payload = AgentChatRequest(
            message="session question",
            sessionId="ags_12345678",
        )

        class SessionService:
            def __init__(self):
                self.history = ()
                self.appended = 0

            def require_owned(self, _user_id, _session_id):
                return None

            def context(self, _user_id, _session_id):
                return self.history

            def append_exchange(
                self,
                _user_id,
                _session_id,
                _request_id,
                user_message,
                assistant_message,
            ):
                self.appended += 1
                self.history += (
                    AgentHistoryMessage(role="user", content=user_message),
                    AgentHistoryMessage(role="assistant", content=assistant_message),
                )

        sessions = SessionService()
        with (
            patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True),
            patch(
                "app.api.v1.routers.agent.get_agent_session_service",
                return_value=sessions,
            ),
            patch(
                "app.api.v1.routers.agent.get_agent_response_replay_cache",
                return_value=cache,
            ),
        ):
            first = await _run_agent_request(payload, {"id": 7}, orchestrator, "request-1")
            replayed = await _run_agent_request(payload, {"id": 7}, orchestrator, "request-1")
            sessions.history += (
                AgentHistoryMessage(role="user", content="later question"),
                AgentHistoryMessage(role="assistant", content="later answer"),
            )
            with self.assertRaises(HTTPException) as conflict:
                await _run_agent_request(payload, {"id": 7}, orchestrator, "request-1")

        self.assertEqual(first, replayed)
        self.assertEqual(1, sessions.appended)
        orchestrator.respond.assert_awaited_once()
        self.assertEqual(409, conflict.exception.status_code)

    async def test_completed_request_is_replayed_without_second_model_call(self):
        from app.api.v1.routers.agent import _run_agent_request

        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        orchestrator = Mock()
        orchestrator.respond = AsyncMock(return_value=response())
        payload = AgentChatRequest(message="介绍 RAG")
        user = {"id": 7}

        with patch(
            "app.api.v1.routers.agent.get_agent_response_replay_cache",
            return_value=cache,
        ):
            first = await _run_agent_request(payload, user, orchestrator, "request-1")
            second = await _run_agent_request(payload, user, orchestrator, "request-1")

        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        orchestrator.respond.assert_awaited_once()

    async def test_same_request_id_with_different_payload_returns_conflict(self):
        from app.api.v1.routers.agent import _run_agent_request

        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        orchestrator = Mock()
        orchestrator.respond = AsyncMock(return_value=response())
        user = {"id": 7}

        with patch(
            "app.api.v1.routers.agent.get_agent_response_replay_cache",
            return_value=cache,
        ):
            await _run_agent_request(
                AgentChatRequest(message="第一个问题"),
                user,
                orchestrator,
                "request-1",
            )
            with self.assertRaises(HTTPException) as raised:
                await _run_agent_request(
                    AgentChatRequest(message="另一个问题"),
                    user,
                    orchestrator,
                    "request-1",
                )

        self.assertEqual(409, raised.exception.status_code)
        self.assertEqual(
            "AGENT_REQUEST_ID_CONFLICT",
            raised.exception.detail["code"],
        )
        orchestrator.respond.assert_awaited_once()

    async def test_cancelled_request_is_not_cached(self):
        from app.api.v1.routers.agent import _run_agent_request

        cache = AgentResponseReplayCache(ttl_seconds=30, max_entries=4)
        orchestrator = Mock()
        started = asyncio.Event()

        async def cancelled_response(*_args, **_kwargs):
            started.set()
            await asyncio.sleep(10)

        orchestrator.respond = cancelled_response
        payload = AgentChatRequest(message="介绍 RAG")
        fingerprint = request_fingerprint(payload)

        with patch(
            "app.api.v1.routers.agent.get_agent_response_replay_cache",
            return_value=cache,
        ):
            task = asyncio.create_task(
                _run_agent_request(payload, {"id": 7}, orchestrator, "request-1")
            )
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertIsNone(cache.get(7, "request-1", fingerprint))


if __name__ == "__main__":
    unittest.main()
