import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routers import common, learning, privacy, user_learning
from app.api.v1.routers.auth import get_current_user
from app.db import database
from app.users.common import UsersError
from app.users.learning_state import LearningStateNotFoundError
from app.users.observability.access import observe_users_request


class _Authorization:
    @staticmethod
    def require_permission(_user_id, permission):
        return {"roles": ["user"], "permissions": [permission]}


class HttpBoundaryTest(unittest.TestCase):
    def test_user_learning_requires_auth_and_scopes_state_to_injected_user(self):
        app = FastAPI()
        app.include_router(user_learning.router, prefix="/api/v1")
        client = TestClient(app)
        self.assertEqual(401, client.get("/api/v1/users/me/learning/progress").status_code)

        active_user = {"id": 11, "user_uid": "usr_11"}
        app.dependency_overrides[get_current_user] = lambda: active_user
        state = Mock()
        state.list_progress.side_effect = lambda user_id: {
            "items": [],
            "meta": {"source": f"users.learning_state:{user_id}", "contractVersion": 1},
        }
        state.node_state.side_effect = LearningStateNotFoundError("not found", "LEARNING_NODE_NOT_FOUND")
        with (
            patch("app.api.v1.dependencies.authorization.get_authorization_service", return_value=_Authorization()),
            patch("app.api.v1.routers.user_learning.get_user_learning_state_service", return_value=state),
        ):
            first = client.get("/api/v1/users/me/learning/progress")
            active_user["id"] = 22
            second = client.get("/api/v1/users/me/learning/progress")
            missing_one = client.get("/api/v1/users/me/learning/nodes/missing")
            active_user["id"] = 11
            missing_two = client.get("/api/v1/users/me/learning/nodes/missing")

        self.assertEqual(200, first.status_code)
        self.assertEqual("users.learning_state:11", first.json()["meta"]["source"])
        self.assertEqual("users.learning_state:22", second.json()["meta"]["source"])
        self.assertEqual(missing_one.status_code, missing_two.status_code)
        self.assertEqual(missing_one.json(), missing_two.json())
        self.assertEqual("LEARNING_NODE_NOT_FOUND", missing_one.json()["detail"]["code"])

    def test_privacy_reauthentication_and_deletion_boundaries_do_not_echo_secrets(self):
        app = FastAPI()
        app.include_router(privacy.router, prefix="/api/v1")
        user = {"id": 11, "user_uid": "usr_11"}
        app.dependency_overrides[get_current_user] = lambda: user
        service = Mock()
        service.export_user_data.side_effect = UsersError("CURRENT_PASSWORD_INVALID", "当前密码错误", 401)
        service.request_deletion.return_value = {
            "request": {"requestUid": "datareq_11", "scheduledFor": "2026-08-01T00:00:00Z"}
        }
        service.cancel_deletion.return_value = {
            "request": {"requestUid": "datareq_11", "status": "cancelled"}
        }
        audit = Mock()
        with (
            patch("app.api.v1.routers.privacy.get_privacy_service", return_value=service),
            patch("app.api.v1.routers.privacy.get_audit_service", return_value=audit),
        ):
            denied = TestClient(app).post(
                "/api/v1/users/me/privacy/export",
                json={"currentPassword": "DoNotEcho123"},
            )
            requested = TestClient(app).post(
                "/api/v1/users/me/privacy/deletion-requests",
                json={"currentPassword": "Current123", "reasonCode": "unused"},
            )
            cancelled = TestClient(app).delete(
                "/api/v1/users/me/privacy/deletion-requests/datareq_11"
            )

        self.assertEqual(401, denied.status_code)
        self.assertEqual("CURRENT_PASSWORD_INVALID", denied.json()["detail"]["code"])
        self.assertNotIn("DoNotEcho123", denied.text)
        self.assertEqual(201, requested.status_code)
        self.assertEqual("cancelled", cancelled.json()["request"]["status"])
        audit.record.assert_called()

    def test_public_learning_and_navigation_do_not_depend_on_agent_provider(self):
        app = FastAPI()
        app.include_router(common.router, prefix="/api/v1")
        app.include_router(learning.router, prefix="/api/v1")
        learning_service = Mock()
        learning_service.search.return_value = {
            "query": "RAG",
            "items": [],
            "meta": {"contractVersion": 1},
        }
        with (
            patch("app.api.v1.routers.learning.get_learning_service", return_value=learning_service),
            patch("app.api.v1.routers.common.get_navigation_items", return_value=[
                {"code": "home", "label": "首页", "href": "index.html"}
            ]),
            patch(
                "app.agent.factory.get_agent_orchestrator",
                side_effect=RuntimeError("provider unavailable"),
            ),
        ):
            client = TestClient(app)
            search = client.get("/api/v1/learning/search?q=RAG")
            navigation = client.get("/api/v1/navigation")

        self.assertEqual(200, search.status_code)
        self.assertEqual([], search.json()["items"])
        self.assertEqual(200, navigation.status_code)
        self.assertEqual("home", navigation.json()["items"][0]["code"])

    def test_users_access_middleware_sanitizes_request_id_and_logs_no_secrets(self):
        app = FastAPI()
        app.middleware("http")(observe_users_request)

        @app.post("/api/v1/auth/login")
        def login_probe():
            return {"status": "ok"}

        with self.assertLogs("app.users.access", level="INFO") as captured:
            response = TestClient(app).post(
                "/api/v1/auth/login",
                headers={
                    "X-Request-Id": "bad injected!",
                    "Authorization": "Bearer secret-token",
                },
                json={"password": "DoNotLog123"},
            )

        self.assertEqual(200, response.status_code)
        self.assertNotEqual("bad injected!", response.headers["X-Request-Id"])
        log_text = "\n".join(captured.output)
        self.assertNotIn("secret-token", log_text)
        self.assertNotIn("DoNotLog123", log_text)
        self.assertNotIn("Authorization", log_text)
        self.assertIn("auth.login", log_text)

    def test_database_initialization_releases_file_without_garbage_collection(self):
        with tempfile.TemporaryDirectory() as temporary:
            database_path = Path(temporary) / "runtime.sqlite3"
            moved_path = Path(temporary) / "runtime-moved.sqlite3"
            with (
                patch.object(database, "DATABASE_PATH", database_path),
                patch.object(database, "RESET_DATABASE_ON_START", False),
            ):
                database.initialize_database()
            database_path.replace(moved_path)
            self.assertTrue(moved_path.exists())
            with closing(sqlite3.connect(moved_path)) as conn:
                self.assertEqual("ok", conn.execute("PRAGMA integrity_check").fetchone()[0])
            moved_path.unlink()
            self.assertFalse(moved_path.exists())


if __name__ == "__main__":
    unittest.main()
