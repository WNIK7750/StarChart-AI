import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from app.agent.replay import (
    AgentReplayConflict,
    AgentResponseReplayCache,
    request_fingerprint,
)
from app.agent.schemas import AgentChatRequest, AgentStructuredResponse


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


class AgentResponseReplayRouteTests(unittest.IsolatedAsyncioTestCase):
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
