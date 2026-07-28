import sqlite3
import tempfile
import unittest
from contextlib import ExitStack
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.agent.sessions import AgentSessionService, AgentSessionStore
from app.api.v1.routers import agent as agent_router
from app.api.v1.routers import auth as auth_router
from app.api.v1.routers import privacy as privacy_router
from app.api.v1.routers import users as users_router
from app.core.security import create_access_token, hash_password, hash_token
from app.db.database import apply_migrations, dict_factory
from app.users.account.repositories.sqlite import SQLiteAccountRepository
from app.users.account.service import AccountService
from app.users.assets.repositories.sqlite import SQLiteAssetsRepository
from app.users.assets.service import AssetsService
from app.users.audit.repositories.sqlite import SQLiteAuditRepository
from app.users.audit.service import AuditService
from app.users.authentication.rate_limit import AuthRateLimiter, SQLiteAuthRateLimitRepository
from app.users.authentication.recovery import MemoryPasswordRecoverySender
from app.users.authentication.repositories.sqlite import SQLiteAuthenticationRepository
from app.users.authentication.service import AuthenticationService
from app.users.authorization.repositories.sqlite import SQLiteAuthorizationRepository
from app.users.authorization.service import AuthorizationService
from app.users import deployment_policy
from app.users.preferences.repositories.sqlite import SQLitePreferencesRepository
from app.users.preferences.service import PreferencesService
from app.users.privacy.repositories.sqlite import SQLitePrivacyRepository
from app.users.privacy.service import PRIVACY_POLICY_VERSION, PrivacyService
from app.users.profile.avatar import AvatarStorage
from app.users.profile.repositories.sqlite import SQLiteProfileRepository
from app.users.profile.service import ProfileService
from app.users.security.repositories.sqlite import SQLiteSecurityRepository
from app.users.security.service import SecurityService
from app.users.sessions.repositories.sqlite import SQLiteSessionsRepository
from app.users.sessions.service import SessionsService

ROOT = Path(__file__).resolve().parents[1]
RESTRICTED_DETAIL = {
    "detail": {
        "code": "DEMO_ACCOUNT_RESTRICTED",
        "message": "当前 HTTP 测试账号不允许执行此操作。",
    }
}


class HttpTestPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        temp_root = Path(self.temp.name)
        self.database_path = temp_root / "policy.sqlite3"
        self.upload_dir = temp_root / "uploads"
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            apply_migrations(conn, ROOT / "database" / "migrations")
            fixtures = (
                (
                    "usr_demo_fixture",
                    "demo_fixture",
                    "demo-fixture@example.test",
                    "+8613800000101",
                    "Demo Fixture",
                    "SyntheticPass123",
                ),
                (
                    "usr_attack_fixture",
                    "attack_fixture",
                    "attack-fixture@example.test",
                    "+8613800000102",
                    "Attack Fixture",
                    "SyntheticPass456",
                ),
            )
            for uid, username, email, phone, display_name, password in fixtures:
                conn.execute(
                    """
                    INSERT INTO user_accounts(
                        user_uid, username, email, phone, account_status
                    ) VALUES (?, ?, ?, ?, 'active')
                    """,
                    (uid, username, email, phone),
                )
                user_id = conn.execute(
                    "SELECT id FROM user_accounts WHERE user_uid = ?",
                    (uid,),
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO user_auth_passwords(user_id, password_hash) VALUES (?, ?)",
                    (user_id, hash_password(password)),
                )
                conn.execute(
                    "INSERT INTO user_profiles(user_id, display_name) VALUES (?, ?)",
                    (user_id, display_name),
                )
                conn.execute("INSERT INTO user_preferences(user_id) VALUES (?)", (user_id,))
                conn.execute(
                    """
                    INSERT INTO user_privacy_consent_events(
                        event_uid, user_id, consent_type, policy_version, action, source
                    ) VALUES (?, ?, 'privacy_policy', ?, 'granted', 'registration')
                    """,
                    (f"cons_{username}", user_id, PRIVACY_POLICY_VERSION),
                )
                conn.execute(
                    """
                    INSERT INTO user_role_assignments(user_id, role_id)
                    SELECT ?, id FROM roles WHERE code = 'user'
                    """,
                    (user_id,),
                )
                conn.execute(
                    """
                    INSERT INTO user_sessions(
                        session_uid, user_id, refresh_token_hash, device_name, expires_at
                    ) VALUES (?, ?, ?, 'fixture device', datetime('now', '+1 day'))
                    """,
                    (f"sess_{username}", user_id, hash_token(f"synthetic-refresh-{username}")),
                )
            conn.commit()
        finally:
            conn.close()

        def connection_factory():
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = dict_factory
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        self.connection_factory = connection_factory
        self.audit = AuditService(SQLiteAuditRepository(connection_factory))
        self.privacy = PrivacyService(SQLitePrivacyRepository(connection_factory))
        self.auth = AuthenticationService(
            SQLiteAuthenticationRepository(connection_factory),
            self.audit,
            self.privacy,
            recovery_sender=MemoryPasswordRecoverySender(),
        )
        self.accounts = AccountService(SQLiteAccountRepository(connection_factory))
        self.profiles = ProfileService(
            SQLiteProfileRepository(connection_factory),
            avatar_storage=AvatarStorage(self.upload_dir),
        )
        self.preferences = PreferencesService(SQLitePreferencesRepository(connection_factory))
        self.sessions = SessionsService(SQLiteSessionsRepository(connection_factory))
        self.security = SecurityService(SQLiteSecurityRepository(connection_factory))
        self.assets = AssetsService(
            SQLiteAssetsRepository(connection_factory),
            self.audit,
            tool_catalog_provider=lambda: {"tools": []},
        )
        self.authorization = AuthorizationService(SQLiteAuthorizationRepository(connection_factory))
        self.agent_sessions = AgentSessionService(AgentSessionStore(connection_factory))
        self.demo_user = self.auth.repository.find_login_user("demo_fixture")
        self.attack_user = self.auth.repository.find_login_user("attack_fixture")
        previous_avatar = self.upload_dir / "avatars" / "previous.webp"
        previous_avatar.parent.mkdir(parents=True, exist_ok=True)
        previous_avatar.write_bytes(b"synthetic previous avatar")
        connection = self.connection_factory()
        try:
            connection.execute(
                """
                UPDATE user_profiles SET avatar_url = '/uploads/avatars/previous.webp'
                WHERE user_id = ?
                """,
                (self.demo_user["id"],),
            )
            connection.commit()
        finally:
            connection.close()
        self.app = FastAPI()
        self.app.include_router(agent_router.router, prefix="/api/v1")
        self.app.include_router(auth_router.router, prefix="/api/v1")
        self.app.include_router(privacy_router.router, prefix="/api/v1")
        self.app.include_router(users_router.router, prefix="/api/v1")
        self.app.dependency_overrides[auth_router.get_current_user] = lambda: self.demo_user

    def tearDown(self):
        self.temp.cleanup()

    def _policy_context(self, environment="http_test"):
        stack = ExitStack()
        stack.enter_context(patch.object(deployment_policy, "APP_ENV", environment))
        stack.enter_context(
            patch.object(
                deployment_policy,
                "HTTP_TEST_ACCOUNT_USERNAME",
                "demo_fixture",
            )
        )
        return stack

    def _service_context(self):
        stack = ExitStack()
        replacements = {
            "app.api.v1.routers.auth.get_authentication_service": self.auth,
            "app.api.v1.routers.auth.get_auth_rate_limiter": AuthRateLimiter(
                SQLiteAuthRateLimitRepository(self.connection_factory)
            ),
            "app.api.v1.routers.users.get_account_service": self.accounts,
            "app.api.v1.routers.users.get_audit_service": self.audit,
            "app.api.v1.routers.users.get_profile_service": self.profiles,
            "app.api.v1.routers.users.get_preferences_service": self.preferences,
            "app.api.v1.routers.users.get_sessions_service": self.sessions,
            "app.api.v1.routers.users.get_security_service": self.security,
            "app.api.v1.routers.users.get_assets_service": self.assets,
            "app.api.v1.routers.privacy.get_privacy_service": self.privacy,
            "app.api.v1.routers.privacy.get_audit_service": self.audit,
            "app.api.v1.dependencies.authorization.get_authorization_service": self.authorization,
            "app.api.v1.routers.agent.get_agent_session_service": self.agent_sessions,
        }
        for target, replacement in replacements.items():
            stack.enter_context(patch(target, return_value=replacement))
        stack.enter_context(patch("app.api.v1.routers.agent.AGENT_SESSIONS_ENABLED", True))
        return stack

    def _assert_restricted(self, response):
        self.assertEqual(403, response.status_code)
        self.assertEqual(RESTRICTED_DETAIL, response.json())

    def _login(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "identifier": " demo_fixture ",
                "password": "SyntheticPass123",
                "privacyAccepted": True,
                "rememberMe": True,
            },
        )
        self.assertEqual(200, response.status_code)
        return response.json()["accessToken"]

    def test_domain_policy_module_exists_and_restricts_http_test_only(self):
        with self._policy_context():
            for action in (
                "register",
                "identity_update",
                "password_update",
                "recovery",
                "security_questions_update",
                "privacy_consent_update",
                "privacy_export",
                "account_deletion_request",
                "account_deletion_cancel",
            ):
                with self.subTest(action=action):
                    with self.assertRaises(deployment_policy.DeploymentPolicyError):
                        deployment_policy.enforce_deployment_action(action)
            deployment_policy.enforce_deployment_action(
                "login",
                login_identifier=" demo_fixture ",
            )
            for label, identifier in (
                ("missing", "missing_fixture"),
                ("other_username", "attack_fixture"),
                ("email_alias", "demo-fixture@example.test"),
                ("phone_alias", "+8613800000101"),
            ):
                with self.subTest(identifier_kind=label):
                    with self.assertRaises(deployment_policy.DeploymentPolicyError) as restricted:
                        deployment_policy.enforce_deployment_action(
                            "login",
                            login_identifier=identifier,
                        )
                    if "demo_fixture" in str(restricted.exception):
                        self.fail("restricted error exposed the configured identifier")

        for environment in ("development", "test"):
            with self.subTest(environment=environment), self._policy_context(environment):
                deployment_policy.enforce_deployment_action("register")
                deployment_policy.enforce_deployment_action(
                    "login",
                    login_identifier="attack_fixture",
                )

    def test_http_test_public_auth_routes_reject_attack_paths_without_enumeration(self):
        with self._policy_context(), self._service_context(), TestClient(self.app) as client:
            restricted_requests = (
                ("get", "/api/v1/auth/username-available?username=unused_fixture", None),
                (
                    "post",
                    "/api/v1/auth/register",
                    {
                        "username": "new_fixture",
                        "password": "SyntheticPass789",
                        "privacyAccepted": True,
                    },
                ),
                (
                    "post",
                    "/api/v1/auth/password-reset/start",
                    {"identifier": "demo_fixture"},
                ),
                (
                    "post",
                    "/api/v1/auth/password-reset/security/start",
                    {"identifier": "attack_fixture"},
                ),
                (
                    "post",
                    "/api/v1/auth/password-reset/security/verify",
                    {"resetUid": "synthetic-reset", "answers": ["synthetic answer"]},
                ),
                (
                    "post",
                    "/api/v1/auth/password-reset/confirm",
                    {
                        "resetToken": "synthetic-reset-token-value",
                        "newPassword": "SyntheticPass789",
                    },
                ),
                (
                    "post",
                    "/api/v1/auth/password-reset/security/confirm",
                    {
                        "resetToken": "synthetic-reset-token-value",
                        "newPassword": "SyntheticPass789",
                    },
                ),
            )
            for method, path, payload in restricted_requests:
                with self.subTest(path=path):
                    response = client.request(method, path, json=payload)
                    self._assert_restricted(response)

            for identifier in (
                "missing_fixture",
                "attack_fixture",
                "demo-fixture@example.test",
                "+8613800000101",
            ):
                response = client.post(
                    "/api/v1/auth/login",
                    json={
                        "identifier": identifier,
                        "password": "SyntheticPass123",
                        "privacyAccepted": True,
                    },
                )
                self._assert_restricted(response)
            self._login(client)
            self.assertEqual(
                2,
                self._database_value("SELECT COUNT(*) FROM user_accounts"),
            )
            self.assertEqual(
                1,
                self._database_value("SELECT COUNT(*) FROM user_login_logs"),
            )

    def test_http_test_rejects_identity_security_and_privacy_writes_before_side_effects(self):
        before_audit_count = self._database_value("SELECT COUNT(*) FROM user_audit_logs")
        with self._policy_context(), self._service_context(), TestClient(self.app) as client:
            restricted_requests = (
                (
                    "patch",
                    "/api/v1/users/me/account",
                    {"username": "renamed_fixture"},
                ),
                (
                    "patch",
                    "/api/v1/users/me/password",
                    {
                        "currentPassword": "SyntheticPass123",
                        "newPassword": "SyntheticPass789",
                    },
                ),
                (
                    "put",
                    "/api/v1/users/me/security-questions",
                    {
                        "currentPassword": "SyntheticPass123",
                        "items": [
                            {"question": "Synthetic question?", "answer": "Synthetic answer"}
                        ],
                    },
                ),
                (
                    "put",
                    "/api/v1/users/me/privacy/consents/agent_memory",
                    {"policyVersion": "synthetic-v1", "granted": True},
                ),
                (
                    "post",
                    "/api/v1/users/me/privacy/export",
                    {"currentPassword": "SyntheticPass123"},
                ),
                (
                    "post",
                    "/api/v1/users/me/privacy/deletion-requests",
                    {"currentPassword": "SyntheticPass123", "reasonCode": "privacy"},
                ),
                (
                    "delete",
                    "/api/v1/users/me/privacy/deletion-requests/req_synthetic",
                    None,
                ),
            )
            for method, path, payload in restricted_requests:
                with self.subTest(path=path):
                    response = client.request(method, path, json=payload)
                    self._assert_restricted(response)

        self.assertEqual(
            before_audit_count,
            self._database_value("SELECT COUNT(*) FROM user_audit_logs"),
        )
        self.assertEqual(
            1,
            self._database_value(
                """
                SELECT COUNT(*) FROM user_accounts
                WHERE user_uid = 'usr_demo_fixture' AND username = 'demo_fixture'
                """
            ),
        )

    def test_http_test_rejects_other_account_refresh_before_rotation_or_audit(self):
        session_count = self._database_value(
            "SELECT COUNT(*) FROM user_sessions WHERE user_id = ?",
            (self.attack_user["id"],),
        )
        audit_count = self._database_value(
            """
            SELECT COUNT(*) FROM user_audit_logs
            WHERE target_user_id = ? AND action = 'users.auth.session_refreshed'
            """,
            (self.attack_user["id"],),
        )
        with self._policy_context(), self._service_context(), TestClient(self.app) as client:
            response = client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": "synthetic-refresh-attack_fixture"},
            )
            self._assert_restricted(response)

        self.assertEqual(
            session_count,
            self._database_value(
                "SELECT COUNT(*) FROM user_sessions WHERE user_id = ?",
                (self.attack_user["id"],),
            ),
        )
        self.assertEqual(
            0,
            self._database_value(
                """
                SELECT COUNT(*) FROM user_sessions
                WHERE user_id = ? AND (is_revoked != 0 OR revoked_reason IS NOT NULL)
                """,
                (self.attack_user["id"],),
            ),
        )
        self.assertEqual(
            audit_count,
            self._database_value(
                """
                SELECT COUNT(*) FROM user_audit_logs
                WHERE target_user_id = ? AND action = 'users.auth.session_refreshed'
                """,
                (self.attack_user["id"],),
            ),
        )

    def test_http_test_rejects_other_account_preexisting_access_token(self):
        access_token = create_access_token(
            {
                "sub": self.attack_user["user_uid"],
                "typ": "access",
                "ver": self.attack_user["token_version"],
            },
            timedelta(minutes=5),
        )
        previous_override = self.app.dependency_overrides.pop(
            auth_router.get_current_user,
        )
        try:
            with self._policy_context(), self._service_context(), TestClient(self.app) as client:
                response = client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                self._assert_restricted(response)
        finally:
            self.app.dependency_overrides[auth_router.get_current_user] = previous_override

    def test_http_test_configured_account_refresh_and_current_user_stay_available(self):
        with self._policy_context(), self._service_context(), TestClient(self.app) as client:
            self._login(client)
            refreshed = client.post("/api/v1/auth/refresh")
            self.assertEqual(200, refreshed.status_code)
            access_token = refreshed.json()["accessToken"]
            previous_override = self.app.dependency_overrides.pop(
                auth_router.get_current_user,
            )
            try:
                current = client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                self.assertEqual(200, current.status_code)
            finally:
                self.app.dependency_overrides[auth_router.get_current_user] = previous_override

    def test_http_test_keeps_profile_preferences_sessions_workflows_logout_and_reads(self):
        with self._policy_context(), self._service_context(), TestClient(self.app) as client:
            access_token = self._login(client)
            headers = {"Authorization": f"Bearer {access_token}"}
            for path in (
                "/api/v1/users/me/account",
                "/api/v1/users/me/profile",
                "/api/v1/users/me/privacy/consents",
                "/api/v1/users/me/privacy/deletion-requests/current",
                "/api/v1/users/me/security-questions",
                "/api/v1/users/me/sessions",
                "/api/v1/users/me/workflows",
                "/api/v1/agent/sessions",
            ):
                with self.subTest(path=path):
                    self.assertEqual(200, client.get(path, headers=headers).status_code)

            profile = client.patch(
                "/api/v1/users/me/profile",
                headers=headers,
                json={"expectedVersion": 1, "bio": "Synthetic bio"},
            )
            self.assertEqual(200, profile.status_code)
            preferences = client.patch(
                "/api/v1/users/me/preferences",
                headers=headers,
                json={"expectedVersion": 1, "theme": "dark"},
            )
            self.assertEqual(200, preferences.status_code)
            agent_session = client.post(
                "/api/v1/agent/sessions",
                headers=headers,
                json={},
            )
            self.assertEqual(201, agent_session.status_code)
            duplicate_unstarted = client.post(
                "/api/v1/agent/sessions",
                headers=headers,
                json={},
            )
            self.assertEqual(409, duplicate_unstarted.status_code)
            self.assertEqual(
                "AGENT_SESSION_UNSTARTED_EXISTS",
                duplicate_unstarted.json()["detail"]["code"],
            )

            image = Image.new("RGB", (8, 8), color=(20, 40, 60))
            image_bytes = BytesIO()
            image.save(image_bytes, format="PNG")
            avatar = client.post(
                "/api/v1/users/me/avatar",
                headers=headers,
                files={"file": ("synthetic.png", image_bytes.getvalue(), "image/png")},
            )
            self.assertEqual(200, avatar.status_code)

            revoked = client.delete(
                "/api/v1/users/me/sessions/sess_demo_fixture",
                headers=headers,
            )
            self.assertEqual(200, revoked.status_code)
            logout = client.post("/api/v1/auth/logout", headers=headers)
            self.assertEqual(200, logout.status_code)

    def test_http_test_account_does_not_gain_admin_privacy_permissions(self):
        with self._policy_context(), self._service_context(), TestClient(self.app) as client:
            for operation in ("execute", "restore", "anonymize"):
                response = client.post(
                    f"/api/v1/users/privacy/deletion-requests/req_synthetic/{operation}"
                )
                with self.subTest(operation=operation):
                    self.assertEqual(403, response.status_code)
                    self.assertEqual("PERMISSION_DENIED", response.json()["detail"]["code"])

    def _database_value(self, query, params=()):
        connection = sqlite3.connect(self.database_path)
        try:
            return connection.execute(query, params).fetchone()[0]
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
