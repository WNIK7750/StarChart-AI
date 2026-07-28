from __future__ import annotations

from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "serve-agent-stage5-acceptance.py"
SPEC = importlib.util.spec_from_file_location("agent_stage5_acceptance", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AgentStage5AcceptanceServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state = MODULE.AcceptanceState()

        def handler(*args, **kwargs):
            return MODULE.Stage5AcceptanceHandler(
                *args,
                delay_seconds=0.01,
                state=state,
                **kwargs,
            )

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method: str, path: str, payload: dict | None = None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=2) as response:
            content = response.read()
            return response.status, json.loads(content) if content else None

    def test_session_and_chat_flow_is_usable_without_external_services(self):
        status, created = self.request("POST", "/api/v1/agent/sessions", {})
        self.assertEqual(201, status)
        session_id = created["session"]["sessionId"]

        with self.assertRaises(HTTPError) as blocked:
            self.request("POST", "/api/v1/agent/sessions", {})
        self.assertEqual(409, blocked.exception.code)

        status, response = self.request(
            "POST",
            "/api/v1/agent/chat",
            {"message": "测试问题", "sessionId": session_id},
        )
        self.assertEqual(200, status)
        self.assertEqual("deterministic", response["meta"]["mode"])
        self.assertIn("模拟回答", response["answer"])

        status, updated = self.request(
            "PATCH",
            f"/api/v1/agent/sessions/{session_id}",
            {"title": "自定义标题", "pinned": True},
        )
        self.assertEqual(200, status)
        self.assertEqual("自定义标题", updated["session"]["title"])
        self.assertTrue(updated["session"]["pinned"])

        status, listed = self.request("GET", "/api/v1/agent/sessions")
        self.assertEqual(200, status)
        self.assertEqual(session_id, listed["items"][0]["sessionId"])
        self.assertEqual(2, listed["items"][0]["messageCount"])

        status, detail = self.request(
            "GET",
            f"/api/v1/agent/sessions/{session_id}?messageLimit=100",
        )
        self.assertEqual(200, status)
        self.assertEqual(["user", "assistant"], [
            item["role"] for item in detail["messages"]
        ])

        status, upgraded = self.request(
            "POST",
            f"/api/v1/agent/sessions/{session_id}/upgrade",
            {},
        )
        self.assertEqual(200, status)
        conversation_id = upgraded["conversation"]["conversationId"]

        with self.assertRaises(HTTPError) as moved:
            self.request("GET", f"/api/v1/agent/sessions/{session_id}")
        self.assertEqual(404, moved.exception.code)
        status, long_list = self.request(
            "GET",
            "/api/v1/agent/long-conversations",
        )
        self.assertEqual(conversation_id, long_list["items"][0]["conversationId"])

        status, _ = self.request(
            "POST",
            "/api/v1/agent/chat",
            {"message": "继续测试", "sessionId": conversation_id},
        )
        self.assertEqual(200, status)
        status, long_detail = self.request(
            "GET",
            f"/api/v1/agent/long-conversations/{conversation_id}",
        )
        self.assertEqual(4, long_detail["meta"]["totalCount"])

        status, second = self.request("POST", "/api/v1/agent/sessions", {})
        self.assertEqual(201, status)
        second_session_id = second["session"]["sessionId"]

        status, payload = self.request(
            "DELETE",
            f"/api/v1/agent/long-conversations/{conversation_id}",
        )
        self.assertEqual(204, status)
        self.assertIsNone(payload)

        with self.assertRaises(HTTPError) as missing:
            self.request(
                "GET",
                f"/api/v1/agent/long-conversations/{conversation_id}",
            )
        self.assertEqual(404, missing.exception.code)
        status, _ = self.request(
            "DELETE",
            f"/api/v1/agent/sessions/{second_session_id}",
        )
        self.assertEqual(204, status)


if __name__ == "__main__":
    unittest.main()
