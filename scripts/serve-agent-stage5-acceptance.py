from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
MAX_REQUEST_BYTES = 8_192


def _timestamp(offset_seconds: int = 0) -> str:
    value = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


class AcceptanceState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sequence = 0
        self._sessions: dict[str, dict] = {}
        self._long_conversations: dict[str, dict] = {}

    @staticmethod
    def _summary(session: dict) -> dict:
        return {
            key: session[key]
            for key in (
                "sessionId",
                "title",
                "messageCount",
                "pinned",
                "pinnedAt",
                "expiresAt",
                "createdAt",
                "updatedAt",
            )
        }

    @staticmethod
    def _meta(total_count: int, limit: int = 20, offset: int = 0) -> dict:
        return {
            "limit": limit,
            "offset": offset,
            "totalCount": total_count,
            "hasNext": offset + limit < total_count,
            "contractVersion": 1,
        }

    @staticmethod
    def _long_summary(conversation: dict) -> dict:
        return {
            key: conversation[key]
            for key in (
                "conversationId",
                "title",
                "messageCount",
                "pinned",
                "pinnedAt",
                "createdAt",
                "updatedAt",
            )
        }

    def create_session(self, title: str | None = None) -> dict | None:
        with self._lock:
            if any(item["messageCount"] == 0 for item in self._sessions.values()):
                return None
            self._sequence += 1
            now = _timestamp()
            session_id = f"ags_{self._sequence:08x}"
            session = {
                "sessionId": session_id,
                "title": (title or "新对话").strip()[:120] or "新对话",
                "messageCount": 0,
                "pinned": False,
                "pinnedAt": None,
                "expiresAt": _timestamp(30 * 60),
                "createdAt": now,
                "updatedAt": now,
                "messages": [],
            }
            self._sessions[session_id] = session
            return self._summary(session)

    def list_sessions(self) -> dict:
        with self._lock:
            sessions = sorted(
                self._sessions.values(),
                key=lambda item: (
                    bool(item["pinned"]),
                    item["pinnedAt"] or "",
                    item["updatedAt"],
                ),
                reverse=True,
            )
            return {
                "items": [self._summary(item) for item in sessions],
                "meta": self._meta(len(sessions)),
            }

    def get_session(self, session_id: str) -> dict | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            messages = [dict(item) for item in session["messages"]]
            return {
                "session": self._summary(session),
                "messages": messages,
                "meta": self._meta(len(messages), limit=100),
            }

    def add_exchange(self, session_id: str, message: str, answer: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            now = _timestamp()
            next_message = len(session["messages"]) + 1
            session["messages"].extend(
                (
                    {
                        "messageId": f"agm_{next_message:08x}",
                        "role": "user",
                        "content": message,
                        "createdAt": now,
                    },
                    {
                        "messageId": f"agm_{next_message + 1:08x}",
                        "role": "assistant",
                        "content": answer,
                        "createdAt": now,
                    },
                )
            )
            if session["title"] == "新对话":
                session["title"] = message[:36]
            session["messageCount"] = len(session["messages"])
            session["updatedAt"] = now
            return True

    def update_session(
        self,
        session_id: str,
        *,
        title: str | None,
        pinned: bool | None,
    ) -> dict | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            if title is not None:
                session["title"] = title
            if pinned is not None:
                session["pinned"] = pinned
                session["pinnedAt"] = (
                    datetime.now(timezone.utc)
                    .isoformat(timespec="microseconds")
                    .replace("+00:00", "Z")
                    if pinned
                    else None
                )
            session["updatedAt"] = _timestamp()
            return self._summary(session)

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def upgrade_session(self, session_id: str) -> tuple[str, dict | None]:
        with self._lock:
            for conversation in self._long_conversations.values():
                if conversation["sourceSessionId"] == session_id:
                    return "existing", self._long_summary(conversation)
            session = self._sessions.get(session_id)
            if not session:
                return "missing", None
            if session["messageCount"] < 2:
                return "unstarted", None
            if len(self._long_conversations) >= 3:
                return "limit", None
            self._sequence += 1
            conversation_id = f"agl_{self._sequence:08x}"
            conversation = {
                **session,
                "conversationId": conversation_id,
                "sourceSessionId": session_id,
            }
            conversation.pop("sessionId", None)
            self._long_conversations[conversation_id] = conversation
            del self._sessions[session_id]
            return "created", self._long_summary(conversation)

    def list_long_conversations(self) -> dict:
        with self._lock:
            conversations = sorted(
                self._long_conversations.values(),
                key=lambda item: (
                    bool(item["pinned"]),
                    item["pinnedAt"] or "",
                    item["updatedAt"],
                ),
                reverse=True,
            )
            return {
                "items": [self._long_summary(item) for item in conversations],
                "meta": self._meta(len(conversations)),
            }

    def get_long_conversation(self, conversation_id: str) -> dict | None:
        with self._lock:
            conversation = self._long_conversations.get(conversation_id)
            if not conversation:
                return None
            messages = [dict(item) for item in conversation["messages"]]
            return {
                "conversation": self._long_summary(conversation),
                "messages": messages,
                "meta": self._meta(len(messages), limit=100),
            }

    def update_long_conversation(
        self,
        conversation_id: str,
        *,
        title: str | None,
        pinned: bool | None,
    ) -> dict | None:
        with self._lock:
            conversation = self._long_conversations.get(conversation_id)
            if not conversation:
                return None
            if title is not None:
                conversation["title"] = title
            if pinned is not None:
                conversation["pinned"] = pinned
                conversation["pinnedAt"] = (
                    datetime.now(timezone.utc)
                    .isoformat(timespec="microseconds")
                    .replace("+00:00", "Z")
                    if pinned
                    else None
                )
            conversation["updatedAt"] = _timestamp()
            return self._long_summary(conversation)

    def delete_long_conversation(self, conversation_id: str) -> bool:
        with self._lock:
            return self._long_conversations.pop(conversation_id, None) is not None

    def has_conversation(self, conversation_id: str) -> bool:
        with self._lock:
            return (
                conversation_id in self._sessions
                or conversation_id in self._long_conversations
            )

    def add_conversation_exchange(
        self,
        conversation_id: str,
        message: str,
        answer: str,
    ) -> bool:
        if conversation_id.startswith("agl_"):
            with self._lock:
                conversation = self._long_conversations.get(conversation_id)
                if not conversation:
                    return False
                now = _timestamp()
                next_message = len(conversation["messages"]) + 1
                conversation["messages"].extend(
                    (
                        {
                            "messageId": f"lgm_{next_message:08x}",
                            "role": "user",
                            "content": message,
                            "createdAt": now,
                        },
                        {
                            "messageId": f"lgm_{next_message + 1:08x}",
                            "role": "assistant",
                            "content": answer,
                            "createdAt": now,
                        },
                    )
                )
                conversation["messageCount"] = len(conversation["messages"])
                conversation["updatedAt"] = now
                return True
        return self.add_exchange(conversation_id, message, answer)


class Stage5AcceptanceHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args,
        delay_seconds: float = 20,
        state: AcceptanceState | None = None,
        **kwargs,
    ):
        self.delay_seconds = delay_seconds
        self.state = state or AcceptanceState()
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._send_json(413, {"detail": "Request too large"})
            return None
        try:
            body = self.rfile.read(length) if length else b"{}"
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"detail": "Invalid JSON"})
            return None
        if not isinstance(payload, dict):
            self._send_json(400, {"detail": "Invalid JSON"})
            return None
        return payload

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/v1/agent/capabilities":
            self._send_json(
                200,
                {"stream": False, "sessions": True, "transportVersion": 1},
            )
            return
        if path == "/api/v1/agent/sessions":
            self._send_json(200, self.state.list_sessions())
            return
        if path == "/api/v1/agent/long-conversations":
            self._send_json(200, self.state.list_long_conversations())
            return
        long_prefix = "/api/v1/agent/long-conversations/"
        if path.startswith(long_prefix):
            result = self.state.get_long_conversation(
                path.removeprefix(long_prefix)
            )
            if result is None:
                self._send_json(404, {"detail": "长期对话不存在"})
            else:
                self._send_json(200, result)
            return
        session_prefix = "/api/v1/agent/sessions/"
        if path.startswith(session_prefix):
            result = self.state.get_session(path.removeprefix(session_prefix))
            if result is None:
                self._send_json(404, {"detail": "会话不存在"})
            else:
                self._send_json(200, result)
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        payload = self._read_json()
        if payload is None:
            return
        if path == "/api/v1/agent/sessions":
            title = payload.get("title")
            if title is not None and not isinstance(title, str):
                self._send_json(422, {"detail": "Invalid title"})
                return
            session = self.state.create_session(title)
            if session is None:
                self._send_json(
                    409,
                    {
                        "detail": {
                            "code": "AGENT_SESSION_UNSTARTED_EXISTS",
                            "message": "请先在当前对话中完成一次问答",
                        }
                    },
                )
                return
            self._send_json(201, {"session": session})
            return
        session_prefix = "/api/v1/agent/sessions/"
        if path.startswith(session_prefix) and path.endswith("/upgrade"):
            session_id = path.removeprefix(session_prefix).removesuffix("/upgrade")
            result, conversation = self.state.upgrade_session(session_id)
            if result == "missing":
                self._send_json(404, {"detail": "会话不存在"})
            elif result == "unstarted":
                self._send_json(
                    409,
                    {
                        "detail": {
                            "code": "AGENT_SESSION_NOT_STARTED",
                            "message": "完成一次问答后才能升级为长期对话",
                        }
                    },
                )
            elif result == "limit":
                self._send_json(
                    409,
                    {
                        "detail": {
                            "code": "AGENT_LONG_CONVERSATION_LIMIT_REACHED",
                            "message": "每个用户最多保存三个长期对话",
                        }
                    },
                )
            else:
                self._send_json(200, {"conversation": conversation})
            return
        if path != "/api/v1/agent/chat":
            self._send_json(404, {"detail": "Not found"})
            return
        message = payload.get("message")
        session_id = payload.get("sessionId")
        if not isinstance(message, str) or not message.strip():
            self._send_json(422, {"detail": "Invalid message"})
            return
        if session_id is not None and (
            not isinstance(session_id, str)
            or not self.state.has_conversation(session_id)
        ):
            self._send_json(404, {"detail": "会话不存在"})
            return
        answer = "这是阶段 5 隔离验收的模拟回答。页面未连接数据库、真实模型或 API Key。"
        time.sleep(self.delay_seconds)
        if session_id:
            self.state.add_conversation_exchange(
                session_id,
                message.strip(),
                answer,
            )
        try:
            self._send_json(
                200,
                {
                    "answer": answer,
                    "intent": "qa",
                    "cards": [],
                    "citations": [],
                    "toolCalls": [],
                    "workflowSteps": [],
                    "workflowDraft": None,
                    "followups": [],
                    "meta": {
                        "source": "agent.deterministic",
                        "contractVersion": 1,
                        "mode": "deterministic",
                        "readOnly": True,
                        "attempts": 0,
                    },
                },
            )
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_PATCH(self) -> None:
        path = urlsplit(self.path).path
        session_prefix = "/api/v1/agent/sessions/"
        long_prefix = "/api/v1/agent/long-conversations/"
        if not path.startswith(session_prefix) and not path.startswith(long_prefix):
            self._send_json(404, {"detail": "Not found"})
            return
        payload = self._read_json()
        if payload is None:
            return
        title = payload.get("title")
        pinned = payload.get("pinned")
        if title is not None:
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
                self._send_json(422, {"detail": "Invalid title"})
                return
            title = title.strip()
        if pinned is not None and not isinstance(pinned, bool):
            self._send_json(422, {"detail": "Invalid pinned state"})
            return
        if title is None and pinned is None:
            self._send_json(422, {"detail": "No update supplied"})
            return
        if path.startswith(long_prefix):
            session = self.state.update_long_conversation(
                path.removeprefix(long_prefix),
                title=title,
                pinned=pinned,
            )
        else:
            session = self.state.update_session(
                path.removeprefix(session_prefix),
                title=title,
                pinned=pinned,
            )
        if session is None:
            self._send_json(404, {"detail": "会话不存在"})
        else:
            key = "conversation" if path.startswith(long_prefix) else "session"
            self._send_json(200, {key: session})

    def do_DELETE(self) -> None:
        path = urlsplit(self.path).path
        session_prefix = "/api/v1/agent/sessions/"
        long_prefix = "/api/v1/agent/long-conversations/"
        if not path.startswith(session_prefix) and not path.startswith(long_prefix):
            self._send_json(404, {"detail": "Not found"})
            return
        deleted = (
            self.state.delete_long_conversation(path.removeprefix(long_prefix))
            if path.startswith(long_prefix)
            else self.state.delete_session(path.removeprefix(session_prefix))
        )
        if deleted:
            self._send_empty(204)
        else:
            self._send_json(404, {"detail": "会话不存在"})

    def log_message(self, format_string: str, *args) -> None:
        print(f"[stage5-acceptance] {self.command} {urlsplit(self.path).path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the Agent Stage 5 frontend acceptance surface.",
    )
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--delay-seconds", type=float, default=20)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    if not 1 <= args.delay_seconds <= 60:
        raise SystemExit("--delay-seconds must be between 1 and 60")

    state = AcceptanceState()
    def handler(*handler_args, **handler_kwargs):
        return Stage5AcceptanceHandler(
            *handler_args,
            delay_seconds=args.delay_seconds,
            state=state,
            **handler_kwargs,
        )
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(
        f"Agent Stage 5 acceptance surface: "
        f"http://127.0.0.1:{args.port}/assistant.html"
    )
    print("Press Ctrl+C to stop. No database, .env, API key, or Provider is used.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
