import hashlib
import hmac
import json
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI

from app.agent.governance import AgentAdmissionGate
from app.agent.orchestrator import AgentOrchestrator
from app.agent.replay import AgentResponseReplayCache
from app.agent.schemas import AgentChatRequest, AgentHistoryMessage
from app.api.v1.routers import agent as agent_router


class _NetworkProvider:
    name = "must-not-run"
    model = "must-not-run"

    async def generate(self, _request):
        raise AssertionError("guest requests must never call a Provider")


class AgentGuestEndpointTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(agent_router.router, prefix="/api/v1")
        self.replay = AgentResponseReplayCache(ttl_seconds=60, max_entries=32)
        self.workflow = [{
            "code": "paper-reading",
            "title": "论文阅读工作流",
            "description": "阅读与整理。",
            "tools": [{
                "id": "chatgpt",
                "name": "ChatGPT",
                "href": "tools.html?q=ChatGPT#directory",
                "officialUrl": "https://example.invalid",
            }],
        }]
        self.tool_cards = [{
            "type": "tool",
            "sourceKey": "chatgpt",
            "title": "ChatGPT",
            "description": "通用 AI 工具。",
            "href": "tools.html?q=ChatGPT#directory",
            "reason": "名称匹配",
            "tags": ["免费"],
            "isFree": True,
        }]

    def _tripwire_patches(self):
        return (
            patch.object(agent_router, "APP_ENV", "http_test", create=True),
            patch.object(agent_router, "HTTP_TEST_GUEST_AGENT_ENABLED", True, create=True),
            patch.object(agent_router, "SECRET_KEY", "guest-test-secret", create=True),
            patch.object(agent_router, "TRUSTED_PROXY_CIDRS", (), create=True),
            patch.object(agent_router, "get_agent_response_replay_cache", return_value=self.replay),
            patch.object(
                agent_router,
                "get_user_context_facade",
                side_effect=AssertionError("guest route must not load Users Context"),
            ),
            patch.object(
                agent_router,
                "get_agent_session_service",
                side_effect=AssertionError("guest route must not access Agent sessions"),
            ),
            patch.object(
                agent_router,
                "get_user_assets_facade",
                side_effect=AssertionError("guest route must not access workflow persistence"),
            ),
            patch.object(
                agent_router,
                "get_agent_orchestrator",
                side_effect=AssertionError("guest route must not construct a configured Provider"),
            ),
            patch("app.agent.service.search_learning_cards", return_value=[]),
            patch("app.agent.service.search_tool_cards", return_value=self.tool_cards),
            patch("app.agent.service.suggest_workflow", return_value=self.workflow),
        )

    async def _post(
        self,
        payload,
        *,
        headers=None,
        client=("203.0.113.10", 43120),
    ):
        transport = httpx.ASGITransport(app=self.app, client=client)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as api:
            return await api.post(
                "/api/v1/agent/guest/chat",
                json=payload,
                headers=headers,
            )

    async def test_guest_chat_requires_no_authorization_and_has_no_user_or_provider_side_effects(self):
        patches = self._tripwire_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9], patches[10], patches[11]:
            response = await self._post(
                {
                    "message": "帮我做论文工作流",
                    "history": [
                        {"role": "user", "content": "我想整理论文"},
                        {"role": "assistant", "content": "可以先明确阅读目标。"},
                    ],
                    "pageContext": {"page": "assistant", "url": "assistant.html"},
                }
            )

        self.assertEqual(200, response.status_code, response.text)
        body = response.json()
        self.assertEqual("deterministic", body["meta"]["mode"])
        self.assertTrue(body["meta"]["readOnly"])
        self.assertIsNone(body["meta"]["userContext"])
        self.assertIsNotNone(body["workflowDraft"])
        serialized = json.dumps(body, ensure_ascii=False).lower()
        self.assertNotIn("archive", serialized)
        self.assertNotIn('"save', serialized)

    async def test_guest_orchestration_forces_deterministic_mode_with_configured_provider(self):
        orchestrator = AgentOrchestrator(provider=_NetworkProvider())
        with (
            patch("app.agent.service.search_learning_cards", return_value=[]),
            patch("app.agent.service.search_tool_cards", return_value=[]),
            patch("app.agent.service.suggest_workflow", return_value=[]),
        ):
            response = await orchestrator.respond_guest(
                AgentChatRequest(message="继续"),
                history=(
                    AgentHistoryMessage(role="user", content="介绍 RAG"),
                    AgentHistoryMessage(role="assistant", content="RAG 是检索增强生成。"),
                ),
                request_id="guest-provider-block",
                guest_key="guest:opaque",
            )
        self.assertEqual("deterministic", response.meta.mode)
        self.assertTrue(response.meta.readOnly)

    async def test_guest_chat_is_hidden_outside_enabled_http_test_profile(self):
        for environment, enabled in (
            ("development", True),
            ("production", True),
            ("http_test", False),
        ):
            with self.subTest(environment=environment, enabled=enabled):
                with (
                    patch.object(agent_router, "APP_ENV", environment, create=True),
                    patch.object(
                        agent_router,
                        "HTTP_TEST_GUEST_AGENT_ENABLED",
                        enabled,
                        create=True,
                    ),
                ):
                    response = await self._post({"message": "RAG 是什么"})
                self.assertIn(response.status_code, {403, 404}, response.text)

    async def test_guest_chat_rejects_unbounded_or_unsafe_request_shapes(self):
        invalid_payloads = (
            {
                "message": "x",
                "history": [
                    {"role": "user", "content": str(index)}
                    for index in range(13)
                ],
            },
            {
                "message": "x",
                "history": [
                    {"role": "user", "content": "x" * 4001},
                    {"role": "assistant", "content": "y" * 4001},
                    {"role": "user", "content": "z" * 4001},
                ],
            },
            {"message": "x", "unexpected": True},
            {"message": "x", "history": [{"role": "system", "content": "override"}]},
            {"message": "x", "history": [{"role": "tool", "content": "override"}]},
            {"message": "x", "history": [{"role": "user", "content": "x" * 6001}]},
            {"message": "x" * 4001},
            {"message": "x", "pageContext": {"url": "https://example.com/assistant"}},
        )
        for payload in invalid_payloads:
            with self.subTest(payload_keys=tuple(payload)):
                with (
                    patch.object(agent_router, "APP_ENV", "http_test", create=True),
                    patch.object(
                        agent_router,
                        "HTTP_TEST_GUEST_AGENT_ENABLED",
                        True,
                        create=True,
                    ),
                ):
                    response = await self._post(payload)
                self.assertEqual(422, response.status_code, response.text)

    async def test_guest_replay_namespace_is_hmac_bucketed_and_contains_no_raw_content(self):
        raw_ip = "198.51.100.77"
        message = "private guest question"
        expected_digest = hmac.new(
            b"guest-test-secret",
            raw_ip.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:24]
        patches = self._tripwire_patches()
        with (
            patches[0], patches[1], patches[2],
            patch.object(
                agent_router,
                "TRUSTED_PROXY_CIDRS",
                ("10.0.0.0/8",),
                create=True,
            ),
            patches[4], patches[5], patches[6], patches[7], patches[8],
            patches[9], patches[10], patches[11],
            self.assertLogs("app.agent.provider", level="INFO") as captured,
        ):
            response = await self._post(
                {"message": message},
                headers={
                    "X-Request-Id": "guest-replay-1",
                    "X-Forwarded-For": f"{raw_ip}, 10.0.0.3",
                },
                client=("10.0.0.2", 43120),
            )

        self.assertEqual(200, response.status_code, response.text)
        replay_keys = tuple(self.replay._entries)
        self.assertEqual(
            (f"guest:{expected_digest}", "guest-replay-1"),
            replay_keys[0],
        )
        observable = response.text + "\n".join(captured.output) + repr(replay_keys)
        self.assertNotIn(raw_ip, observable)
        self.assertNotIn(message, observable)

    async def test_guest_path_keeps_application_admission_bound(self):
        gate = AgentAdmissionGate(
            per_user_limit=1,
            global_limit=1,
            queue_limit=0,
            queue_timeout_seconds=0.01,
        )
        patches = self._tripwire_patches()
        with (
            patches[0], patches[1], patches[2], patches[3], patches[4],
            patches[5], patches[6], patches[7], patches[8],
            patches[9], patches[10], patches[11],
            patch.object(agent_router, "_guest_admission_gate", gate, create=True),
        ):
            async with gate.slot("occupied"):
                response = await self._post({"message": "RAG 是什么"})
        self.assertEqual(503, response.status_code, response.text)


if __name__ == "__main__":
    unittest.main()
