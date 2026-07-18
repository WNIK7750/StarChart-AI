import json
import sqlite3
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request, Response
from PIL import Image
from pydantic import ValidationError

from app.api.v1.routers import auth as auth_router
from app.api.v1.routers.common import check_database_ready, health_live
from app.api.v1.routers import users as users_router
from app.api.v1.dependencies.authorization import require_permission
from app.api.v1.routers.users import ProfileUpdate
from app.agent.memory import load_user_agent_preferences
from app.agent.schemas import AgentChatRequest
from app.agent.service import draft_agent_response
from app.db.database import apply_migrations, dict_factory
from app.core.security import hash_password, hash_token
from app.core.config import DEV_SECRET_KEY, PASSWORD_HASH_ROUNDS, validate_runtime_security
from app.users.account.repositories.sqlite import SQLiteAccountRepository
from app.users.account.service import AccountService
from app.users.assets.facade import UserAssetsFacade
from app.users.assets.repositories.sqlite import SQLiteAssetsRepository
from app.users.assets.schemas import WorkflowCreate
from app.users.assets.service import AssetsService
from app.users.audit.repositories.sqlite import SQLiteAuditRepository
from app.users.audit.service import AuditService
from app.users.authorization.repositories.sqlite import SQLiteAuthorizationRepository
from app.users.authorization.service import AuthorizationService
from app.users.authentication.repositories.sqlite import SQLiteAuthenticationRepository
from app.users.authentication.rate_limit import AuthRateLimiter, SQLiteAuthRateLimitRepository
from app.users.authentication.service import AuthenticationService, RequestContext
from app.users.common import StrictModel, UsersError
from app.users.preferences.repositories.sqlite import SQLitePreferencesRepository
from app.users.preferences.facade import UserPreferencesFacade
from app.users.preferences.service import PreferencesService
from app.users.privacy.repositories.sqlite import SQLitePrivacyRepository
from app.users.privacy.service import AGENT_MEMORY_POLICY_VERSION, PRIVACY_POLICY_VERSION, PrivacyService
from app.users.profile.avatar import AvatarProcessor, AvatarStorage
from app.users.profile.repositories.sqlite import SQLiteProfileRepository
from app.users.profile.service import ProfileService
from app.users.context.facade import UserContextFacade
from app.users.observability.access import request_id
from app.users.observability.metrics import UsersMetrics
from app.users.security.repositories.sqlite import SQLiteSecurityRepository
from app.users.security.service import SecurityService
from app.users.sessions.repositories.sqlite import SQLiteSessionsRepository
from app.users.sessions.service import SessionsService


ROOT = Path(__file__).resolve().parents[1]


class ExampleStrictPayload(StrictModel):
    name: str


class UsersServicesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "users.sqlite3"
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            apply_migrations(conn, ROOT / "database" / "migrations")
            users = [
                ("usr_alice", "alice", "alice@example.test", "Alice"),
                ("usr_bob", "bob", "bob@example.test", "Bob"),
            ]
            for uid, username, email, display_name in users:
                conn.execute(
                    "INSERT INTO user_accounts(user_uid, username, email, account_status) VALUES (?, ?, ?, 'active')",
                    (uid, username, email),
                )
                user_id = conn.execute("SELECT id FROM user_accounts WHERE user_uid = ?", (uid,)).fetchone()[0]
                conn.execute(
                    "INSERT INTO user_auth_passwords(user_id, password_hash) VALUES (?, ?)",
                    (user_id, hash_password("Current123")),
                )
                conn.execute("INSERT INTO user_profiles(user_id, display_name) VALUES (?, ?)", (user_id, display_name))
                conn.execute("INSERT INTO user_preferences(user_id) VALUES (?)", (user_id,))
                conn.execute(
                    """
                    INSERT INTO user_privacy_consent_events(
                        event_uid, user_id, consent_type, policy_version, action, source
                    ) VALUES (?, ?, 'privacy_policy', '2026-07-01', 'granted', 'registration')
                    """,
                    (f"cons_{username}", user_id),
                )
                conn.execute(
                    "INSERT INTO user_role_assignments(user_id, role_id) SELECT ?, id FROM roles WHERE code = 'user'",
                    (user_id,),
                )
                conn.execute(
                    """
                    INSERT INTO user_sessions(session_uid, user_id, refresh_token_hash, device_name, expires_at)
                    VALUES (?, ?, ?, 'test device', datetime('now', '+1 day'))
                    """,
                    (f"sess_{username}", user_id, hash_token(f"refresh-{username}")),
                )
            self.alice_id = conn.execute("SELECT id FROM user_accounts WHERE user_uid = 'usr_alice'").fetchone()[0]
            self.bob_id = conn.execute("SELECT id FROM user_accounts WHERE user_uid = 'usr_bob'").fetchone()[0]
            conn.commit()
        finally:
            conn.close()

        def connection_factory():
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = dict_factory
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

        self.connection_factory = connection_factory
        self.accounts = AccountService(SQLiteAccountRepository(connection_factory))
        self.audit = AuditService(SQLiteAuditRepository(connection_factory))
        self.assets = AssetsService(
            SQLiteAssetsRepository(connection_factory),
            self.audit,
            tool_catalog_provider=lambda: {"tools": []},
        )
        self.profiles = ProfileService(SQLiteProfileRepository(connection_factory))
        self.preferences = PreferencesService(SQLitePreferencesRepository(connection_factory))
        self.privacy = PrivacyService(SQLitePrivacyRepository(connection_factory))
        self.sessions = SessionsService(SQLiteSessionsRepository(connection_factory))
        self.security = SecurityService(SQLiteSecurityRepository(connection_factory))
        self.authorization = AuthorizationService(SQLiteAuthorizationRepository(connection_factory))
        self.auth = AuthenticationService(SQLiteAuthenticationRepository(connection_factory), self.audit, self.privacy)
        self.context = RequestContext(ip_address="127.0.0.1", user_agent="users-test")

    def tearDown(self):
        self.temp.cleanup()

    def database_value(self, query, params=()):
        conn = sqlite3.connect(self.database_path)
        try:
            return conn.execute(query, params).fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def avatar_bytes(size=(900, 600), image_format="PNG"):
        output = BytesIO()
        Image.new("RGBA", size, (30, 120, 210, 180)).save(output, format=image_format)
        return output.getvalue()

    def test_strict_payload_rejects_extra_fields(self):
        ExampleStrictPayload.model_validate({"name": "ok"})
        with self.assertRaises(ValidationError):
            ExampleStrictPayload.model_validate({"name": "ok", "extra": True})
        with self.assertRaises(ValidationError):
            ProfileUpdate.model_validate({"expectedVersion": 1, "avatarUrl": "https://example.test/avatar.png"})

    def test_avatar_processing_rejects_spoofed_and_oversized_pixels(self):
        content = self.avatar_bytes(size=(40, 40))
        processor = AvatarProcessor(max_source_pixels=10_000)
        with self.assertRaises(UsersError) as mismatch:
            processor.process(content, "image/jpeg")
        self.assertEqual("AVATAR_CONTENT_TYPE_MISMATCH", mismatch.exception.code)
        with self.assertRaises(UsersError) as pixel_limit:
            AvatarProcessor(max_source_pixels=100).process(content, "image/png")
        self.assertEqual("AVATAR_PIXEL_LIMIT_EXCEEDED", pixel_limit.exception.code)
        self.assertEqual(413, pixel_limit.exception.status_code)

    def test_avatar_upload_replaces_old_file_and_rolls_back_failed_profile_update(self):
        upload_dir = Path(self.temp.name) / "uploads"
        service = ProfileService(
            self.profiles.repository,
            AvatarProcessor(max_output_bytes=120_000, max_dimension=256, max_source_pixels=2_000_000),
            AvatarStorage(upload_dir),
        )
        first = service.upload_avatar(self.alice_id, self.avatar_bytes(), "image/png")
        first_path = upload_dir / "avatars" / Path(first["avatarUrl"]).name
        self.assertTrue(first_path.exists())
        self.assertEqual("webp", first["meta"]["format"])
        self.assertLessEqual(first["meta"]["width"], 256)
        self.assertLessEqual(first["meta"]["height"], 256)

        second = service.upload_avatar(self.alice_id, self.avatar_bytes(size=(640, 640)), "image/png")
        second_path = upload_dir / "avatars" / Path(second["avatarUrl"]).name
        self.assertFalse(first_path.exists())
        self.assertTrue(second_path.exists())
        self.assertTrue(second["meta"]["oldAvatarRemoved"])
        before_failure = sorted(path.name for path in (upload_dir / "avatars").glob("*"))
        with self.assertRaises(UsersError) as missing:
            service.upload_avatar(999_999, self.avatar_bytes(size=(128, 128)), "image/png")
        self.assertEqual("PROFILE_NOT_FOUND", missing.exception.code)
        self.assertEqual(before_failure, sorted(path.name for path in (upload_dir / "avatars").glob("*")))
        self.assertEqual([], list((upload_dir / "avatars").glob("*.tmp")))

    def test_account_update_is_isolated_and_reports_conflict(self):
        with self.assertRaises(UsersError) as conflict:
            self.accounts.update_account(self.alice_id, {"username": "bob"})
        self.assertEqual("USERNAME_TAKEN", conflict.exception.code)
        self.assertEqual(409, conflict.exception.status_code)
        updated = self.accounts.update_account(self.alice_id, {"username": "alice-new"})["account"]
        self.assertEqual("alice-new", updated["username"])
        self.assertEqual("bob", self.accounts.get_account(self.bob_id)["account"]["username"])

    def test_account_contact_update_requires_password_normalizes_and_resets_verification(self):
        conn = self.connection_factory()
        try:
            conn.execute(
                "UPDATE user_accounts SET phone = '+8613900000000', email_verified = 1, phone_verified = 1 WHERE id = ?",
                (self.alice_id,),
            )
            conn.execute("UPDATE user_accounts SET phone = '+8613800000001' WHERE id = ?", (self.bob_id,))
            conn.commit()
        finally:
            conn.close()

        with self.assertRaises(UsersError) as password_required:
            self.accounts.update_account(self.alice_id, {"email": "new@example.test"})
        self.assertEqual(("CURRENT_PASSWORD_INVALID", 401), (password_required.exception.code, password_required.exception.status_code))
        with self.assertRaises(UsersError) as duplicate_email:
            self.accounts.update_account(
                self.alice_id,
                {"email": "BOB@EXAMPLE.TEST", "currentPassword": "Current123"},
            )
        self.assertEqual("EMAIL_TAKEN", duplicate_email.exception.code)
        with self.assertRaises(UsersError) as duplicate_phone:
            self.accounts.update_account(
                self.alice_id,
                {"phone": "138 0000 0001", "currentPassword": "Current123"},
            )
        self.assertEqual("PHONE_TAKEN", duplicate_phone.exception.code)

        updated = self.accounts.update_account(
            self.alice_id,
            {
                "email": "Alice.New@Example.Test",
                "phone": "138-0000-0000",
                "currentPassword": "Current123",
            },
        )["account"]
        self.assertEqual(("alice.new@example.test", "+8613800000000"), (updated["email"], updated["phone"]))
        self.assertFalse(updated["emailVerified"])
        self.assertFalse(updated["phoneVerified"])

    def test_profile_and_preferences_update_only_current_user(self):
        profile = self.profiles.update_profile(
            self.alice_id,
            {"displayName": "Alice A.", "bio": "  learning  ", "learningLevel": "intermediate"},
            1,
        )["profile"]
        prefs = self.preferences.update_preferences(
            self.alice_id,
            {"theme": "dark", "cnFirst": False, "agentMemoryEnabled": True},
            1,
        )["preferences"]
        self.assertEqual("Alice A.", profile["displayName"])
        self.assertEqual("learning", profile["bio"])
        self.assertEqual("dark", prefs["theme"])
        self.assertFalse(prefs["cnFirst"])
        self.assertTrue(prefs["agentMemoryEnabled"])
        self.assertEqual("Bob", self.profiles.get_profile(self.bob_id)["profile"]["displayName"])
        self.assertEqual("light", self.preferences.get_preferences(self.bob_id)["preferences"]["theme"])

    def test_profile_update_rejects_stale_version(self):
        first = self.profiles.update_profile(self.alice_id, {"displayName": "First"}, 1)["profile"]
        self.assertEqual(2, first["version"])
        with self.assertRaises(UsersError) as conflict:
            self.profiles.update_profile(self.alice_id, {"displayName": "Stale"}, 1)
        self.assertEqual("PROFILE_VERSION_CONFLICT", conflict.exception.code)
        self.assertEqual(409, conflict.exception.status_code)
        current = self.profiles.get_profile(self.alice_id)["profile"]
        self.assertEqual("First", current["displayName"])
        self.assertEqual(2, current["version"])

    def test_preferences_update_rejects_stale_version(self):
        first = self.preferences.update_preferences(self.alice_id, {"theme": "dark"}, 1)["preferences"]
        self.assertEqual(2, first["version"])
        with self.assertRaises(UsersError) as conflict:
            self.preferences.update_preferences(self.alice_id, {"theme": "system"}, 1)
        self.assertEqual("PREFERENCES_VERSION_CONFLICT", conflict.exception.code)
        self.assertEqual(409, conflict.exception.status_code)
        current = self.preferences.get_preferences(self.alice_id)["preferences"]
        self.assertEqual("dark", current["theme"])
        self.assertEqual(2, current["version"])

    def test_preferences_facade_projects_consumer_fields_without_client_copy(self):
        self.preferences.update_preferences(
            self.alice_id,
            {"language": "zh-CN", "cnFirst": False, "freeFirst": True, "agentMemoryEnabled": True},
            1,
        )
        facade = UserPreferencesFacade(self.preferences, self.privacy)
        learning = facade.get_context(self.alice_id, "learning")
        agent = load_user_agent_preferences(self.alice_id, facade)
        self.assertEqual("users.preferences", learning["meta"]["source"])
        self.assertEqual("learning", learning["meta"]["consumer"])
        self.assertNotIn("agentMemoryEnabled", learning["preferences"])
        self.assertTrue(agent["preferences"]["freeFirst"])
        self.assertFalse(agent["preferences"]["agentMemoryEnabled"])
        self.privacy.set_consent(
            self.alice_id,
            "agent_memory",
            AGENT_MEMORY_POLICY_VERSION,
            True,
        )
        agent = load_user_agent_preferences(self.alice_id, facade)
        self.assertTrue(agent["preferences"]["agentMemoryEnabled"])
        with self.assertRaises(ValidationError):
            AgentChatRequest.model_validate({"message": "hello", "preferences": {"freeFirst": False}})
        cards = [
            {"type": "tool", "sourceKey": "paid", "title": "Paid", "description": "", "href": "tools.html", "tags": ["商用"], "isFree": False},
            {"type": "tool", "sourceKey": "free", "title": "Free", "description": "", "href": "tools.html", "tags": ["免费"], "isFree": True},
        ]
        with (
            patch("app.agent.service.search_tool_cards", return_value=cards),
            patch("app.agent.service.search_learning_cards", return_value=[]),
            patch("app.agent.service.suggest_workflow", return_value=[]),
        ):
            response = draft_agent_response(AgentChatRequest(message="recommend"), agent)
        self.assertEqual(["Free", "Paid"], [card.title for card in response.cards])
        self.assertNotIn("是否需要免费工具优先？", response.followups)

    def test_privacy_consent_is_versioned_revocable_and_authoritative_for_agent(self):
        status = self.privacy.consent_status(self.alice_id)
        agent = next(item for item in status["items"] if item["consentType"] == "agent_memory")
        self.assertEqual(("revoked", AGENT_MEMORY_POLICY_VERSION), (agent["status"], agent["policyVersion"]))
        with self.assertRaises(UsersError) as stale:
            self.privacy.set_consent(self.alice_id, "agent_memory", "2025-01-01", True)
        self.assertEqual(("CONSENT_VERSION_OUTDATED", 409), (stale.exception.code, stale.exception.status_code))

        granted = self.privacy.set_consent(
            self.alice_id,
            "agent_memory",
            AGENT_MEMORY_POLICY_VERSION,
            True,
        )
        self.assertEqual("granted", granted["consent"]["status"])
        self.assertTrue(self.privacy.has_current_consent(self.alice_id, "agent_memory"))
        revoked = self.privacy.set_consent(
            self.alice_id,
            "agent_memory",
            AGENT_MEMORY_POLICY_VERSION,
            False,
        )
        self.assertEqual("revoked", revoked["consent"]["status"])
        self.assertFalse(self.privacy.has_current_consent(self.alice_id, "agent_memory"))
        self.assertEqual(
            2,
            self.database_value(
                "SELECT COUNT(*) FROM user_privacy_consent_events WHERE user_id = ? AND consent_type = 'agent_memory'",
                (self.alice_id,),
            ),
        )

    def test_data_export_requires_reauthentication_and_excludes_authentication_secrets(self):
        with self.assertRaises(UsersError) as invalid:
            self.privacy.export_user_data(self.alice_id, "WrongPassword123")
        self.assertEqual(("CURRENT_PASSWORD_INVALID", 401), (invalid.exception.code, invalid.exception.status_code))

        self.privacy.set_consent(
            self.alice_id,
            "privacy_policy",
            PRIVACY_POLICY_VERSION,
            True,
        )
        exported = self.privacy.export_user_data(self.alice_id, "Current123")
        serialized = json.dumps(exported, ensure_ascii=False)
        self.assertEqual("completed", exported["request"]["status"])
        self.assertEqual("alice@example.test", exported["export"]["data"]["account"]["email"])
        self.assertNotIn("bob@example.test", serialized)
        for forbidden in ("password_hash", "refresh_token_hash", "answer_hash", "Current123"):
            self.assertNotIn(forbidden, serialized)

    def test_deletion_lifecycle_is_scoped_recoverable_and_anonymizes_only_private_data(self):
        first = self.privacy.request_deletion(self.alice_id, "Current123", "privacy")["request"]
        with self.assertRaises(UsersError) as cross_user:
            self.privacy.cancel_deletion(self.bob_id, first["requestUid"])
        self.assertEqual("DELETION_REQUEST_NOT_CANCELLABLE", cross_user.exception.code)
        cancelled = self.privacy.cancel_deletion(self.alice_id, first["requestUid"])["request"]
        self.assertEqual("cancelled", cancelled["status"])

        second = self.privacy.request_deletion(self.alice_id, "Current123", "unused")["request"]
        conn = self.connection_factory()
        try:
            conn.execute(
                "UPDATE user_data_requests SET scheduled_for = datetime('now', '-1 day') WHERE request_uid = ?",
                (second["requestUid"],),
            )
            conn.commit()
        finally:
            conn.close()
        executed = self.privacy.execute_deletion(second["requestUid"])
        self.assertEqual("processing", executed["request"]["status"])
        self.assertEqual("deleted", self.database_value("SELECT account_status FROM user_accounts WHERE id = ?", (self.alice_id,)))
        restored = self.privacy.restore_deletion(second["requestUid"])
        self.assertEqual("cancelled", restored["request"]["status"])
        self.assertEqual("active", self.database_value("SELECT account_status FROM user_accounts WHERE id = ?", (self.alice_id,)))

        self.privacy.set_consent(
            self.alice_id,
            "agent_memory",
            AGENT_MEMORY_POLICY_VERSION,
            True,
        )
        public_nodes_before = self.database_value("SELECT COUNT(*) FROM roadmap_nodes")
        third = self.privacy.request_deletion(self.alice_id, "Current123", "other")["request"]
        conn = self.connection_factory()
        try:
            conn.execute(
                "UPDATE user_data_requests SET scheduled_for = datetime('now', '-1 day') WHERE request_uid = ?",
                (third["requestUid"],),
            )
            conn.commit()
        finally:
            conn.close()
        self.privacy.execute_deletion(third["requestUid"])
        conn = self.connection_factory()
        try:
            conn.execute(
                "UPDATE user_data_requests SET retention_until = datetime('now', '-1 minute') WHERE request_uid = ?",
                (third["requestUid"],),
            )
            conn.commit()
        finally:
            conn.close()
        anonymized = self.privacy.anonymize_deletion(third["requestUid"])
        self.assertEqual("completed", anonymized["request"]["status"])
        self.assertIsNone(self.database_value("SELECT username FROM user_accounts WHERE id = ?", (self.alice_id,)))
        self.assertEqual("已注销用户", self.database_value("SELECT display_name FROM user_profiles WHERE user_id = ?", (self.alice_id,)))
        self.assertEqual(0, self.database_value("SELECT COUNT(*) FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,)))
        self.assertEqual(0, self.database_value("SELECT COUNT(*) FROM user_sessions WHERE user_id = ?", (self.alice_id,)))
        self.assertEqual(1, self.database_value("SELECT COUNT(*) FROM user_sessions WHERE user_id = ?", (self.bob_id,)))
        self.assertEqual(public_nodes_before, self.database_value("SELECT COUNT(*) FROM roadmap_nodes"))
        self.assertFalse(self.privacy.has_current_consent(self.alice_id, "agent_memory"))

    def test_workflow_assets_are_idempotent_versioned_archivable_and_user_scoped(self):
        context = {
            "actorUserId": self.alice_id,
            "targetUserId": self.alice_id,
            "ipAddress": "127.0.0.1",
            "userAgent": "assets-test",
        }
        payload = {
            "title": "Research workflow",
            "description": "Collect and summarize sources",
            "sourceType": "agent",
            "sourceRef": "paper-reading",
            "confirmed": True,
            "steps": [
                {
                    "order": 1,
                    "name": "Search",
                    "objective": "Find sources",
                    "toolSlug": "retired-tool",
                    "toolNameSnapshot": "Retired Tool",
                    "toolHrefSnapshot": "https://example.test/retired",
                }
            ],
        }
        created = self.assets.create_workflow(self.alice_id, payload, "workflow-save-001", context)
        replayed = self.assets.create_workflow(self.alice_id, payload, "workflow-save-001", context)
        workflow = created["workflow"]
        self.assertFalse(created["meta"]["idempotencyReplayed"])
        self.assertTrue(replayed["meta"]["idempotencyReplayed"])
        self.assertEqual(workflow["workflowUid"], replayed["workflow"]["workflowUid"])
        self.assertEqual("degraded", workflow["availability"]["status"])
        self.assertEqual("unavailable", workflow["steps"][0]["target"]["status"])
        self.assertEqual("Retired Tool", workflow["steps"][0]["target"]["name"])
        self.assertEqual(1, self.assets.list_workflows(self.alice_id)["meta"]["totalCount"])
        self.assertEqual(0, self.assets.list_workflows(self.bob_id)["meta"]["totalCount"])
        with self.assertRaises(UsersError) as cross_user:
            self.assets.get_workflow(self.bob_id, workflow["workflowUid"])
        self.assertEqual("WORKFLOW_NOT_FOUND", cross_user.exception.code)

        updated = self.assets.update_workflow(
            self.alice_id,
            workflow["workflowUid"],
            workflow["version"],
            {"title": "Updated workflow"},
            context,
        )["workflow"]
        self.assertEqual(2, updated["version"])
        with self.assertRaises(UsersError) as stale:
            self.assets.update_workflow(
                self.alice_id,
                workflow["workflowUid"],
                workflow["version"],
                {"title": "Stale"},
                context,
            )
        self.assertEqual(("WORKFLOW_VERSION_CONFLICT", 409), (stale.exception.code, stale.exception.status_code))
        archived = self.assets.set_status(
            self.alice_id, workflow["workflowUid"], updated["version"], "archived", context
        )["workflow"]
        self.assertEqual("archived", archived["status"])
        restored = self.assets.set_status(
            self.alice_id, workflow["workflowUid"], archived["version"], "active", context
        )["workflow"]
        self.assertEqual("active", restored["status"])
        self.assertEqual(
            4,
            self.database_value(
                "SELECT COUNT(*) FROM user_audit_logs WHERE actor_user_id = ? AND resource_type = 'saved_workflow'",
                (self.alice_id,),
            ),
        )

    def test_agent_context_is_minimal_and_includes_asset_summary(self):
        context = {
            "actorUserId": self.alice_id,
            "targetUserId": self.alice_id,
            "ipAddress": None,
            "userAgent": "context-test",
        }
        self.assets.create_workflow(
            self.alice_id,
            {
                "title": "Saved plan",
                "description": None,
                "sourceType": "manual",
                "sourceRef": None,
                "confirmed": True,
                "steps": [{"order": 1, "name": "Plan", "objective": "Outline", "toolSlug": None}],
            },
            "context-workflow-001",
            context,
        )
        facade = UserContextFacade(
            UserPreferencesFacade(self.preferences, self.privacy),
            self.authorization,
            UserAssetsFacade(self.assets),
        )
        result = facade.for_agent(self.alice_id)
        self.assertTrue(result["capabilities"]["agentChat"])
        self.assertEqual(1, result["assets"]["activeCount"])
        self.assertEqual("Saved plan", result["assets"]["recent"][0]["title"])
        self.assertNotIn("email", json.dumps(result))
        self.assertNotIn("roles", result)

    def test_agent_workflow_save_requires_explicit_confirmation(self):
        base = {
            "title": "Confirmed workflow",
            "sourceType": "agent",
            "confirmed": True,
            "steps": [{"order": 1, "name": "Draft", "objective": "Prepare", "toolSlug": None}],
        }
        validated = WorkflowCreate.model_validate(base)
        self.assertTrue(validated.confirmed)
        with self.assertRaises(ValidationError):
            WorkflowCreate.model_validate({**base, "confirmed": False})

    def test_sessions_are_user_scoped_and_revocable(self):
        alice_result = self.sessions.list_sessions(self.alice_id)
        alice_sessions = alice_result["items"]
        self.assertEqual(["sess_alice"], [item["sessionUid"] for item in alice_sessions])
        self.assertEqual({"page": 1, "pageSize": 20, "totalCount": 1, "hasNext": False, "source": "users.sessions", "contractVersion": 2}, alice_result["meta"])
        with self.assertRaises(UsersError) as cross_user:
            self.sessions.revoke_session(self.alice_id, "sess_bob")
        self.assertEqual(("SESSION_NOT_FOUND", 404), (cross_user.exception.code, cross_user.exception.status_code))
        self.assertEqual(0, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_bob'"))
        self.sessions.revoke_session(self.alice_id, "sess_alice")
        self.assertEqual(1, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual("logout", self.database_value("SELECT revoked_reason FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual(0, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_bob'"))

    def test_sessions_mark_current_and_revoke_other_devices(self):
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute(
                """
                INSERT INTO user_sessions(session_uid, user_id, refresh_token_hash, device_name, expires_at)
                VALUES ('sess_alice_phone', ?, ?, 'phone', datetime('now', '+1 day'))
                """,
                (self.alice_id, hash_token("refresh-alice-phone")),
            )
            conn.execute(
                """
                INSERT INTO user_sessions(session_uid, user_id, refresh_token_hash, device_name, is_revoked, revoked_reason, expires_at)
                VALUES ('sess_alice_replay', ?, ?, 'old phone', 1, 'replay_detected', datetime('now', '+1 day'))
                """,
                (self.alice_id, hash_token("refresh-alice-replay")),
            )
            conn.commit()
        finally:
            conn.close()

        result = self.sessions.list_sessions(self.alice_id, current_refresh_token_hash=hash_token("refresh-alice"))
        by_uid = {item["sessionUid"]: item for item in result["items"]}
        self.assertTrue(by_uid["sess_alice"]["isCurrent"])
        self.assertFalse(by_uid["sess_alice_phone"]["isCurrent"])
        self.assertEqual("normal", by_uid["sess_alice"]["riskLevel"])
        self.assertEqual("high", by_uid["sess_alice_replay"]["riskLevel"])

        revoked = self.sessions.revoke_other_sessions(self.alice_id, hash_token("refresh-alice"))
        self.assertEqual({"status": "ok", "revokedCount": 1}, revoked)
        self.assertEqual(0, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual(1, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_alice_phone'"))
        self.assertEqual(0, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_bob'"))

    def test_sessions_pagination_metadata(self):
        conn = sqlite3.connect(self.database_path)
        try:
            for index in range(2, 5):
                conn.execute(
                    """
                    INSERT INTO user_sessions(session_uid, user_id, refresh_token_hash, device_name, expires_at)
                    VALUES (?, ?, ?, ?, datetime('now', '+1 day'))
                    """,
                    (f"sess_alice_{index}", self.alice_id, hash_token(f"refresh-alice-{index}"), f"device {index}"),
                )
            conn.commit()
        finally:
            conn.close()
        first_page = self.sessions.list_sessions(self.alice_id, page=1, page_size=2)
        second_page = self.sessions.list_sessions(self.alice_id, page=2, page_size=2)
        self.assertEqual(4, first_page["meta"]["totalCount"])
        self.assertTrue(first_page["meta"]["hasNext"])
        self.assertFalse(second_page["meta"]["hasNext"])
        self.assertEqual(2, len(first_page["items"]))
        self.assertEqual(2, len(second_page["items"]))

    def test_authorization_facade_reads_roles_and_permissions(self):
        context = self.authorization.user_context(self.alice_id)
        self.assertIn("user", context["roles"])
        self.assertIn("learning:read", context["permissions"])

    def test_role_permission_matrix_and_api_dependency_return_stable_403(self):
        user_context = self.authorization.require_permission(self.alice_id, "agent:chat")
        self.assertEqual(["user"], user_context["roles"])
        with self.assertRaises(UsersError) as denied:
            self.authorization.require_permission(self.alice_id, "users:manage")
        self.assertEqual(("PERMISSION_DENIED", 403), (denied.exception.code, denied.exception.status_code))

        conn = self.connection_factory()
        try:
            conn.execute(
                "INSERT INTO user_role_assignments(user_id, role_id) SELECT ?, id FROM roles WHERE code = 'operator'",
                (self.bob_id,),
            )
            conn.execute(
                """
                INSERT INTO user_role_assignments(user_id, role_id, expires_at)
                SELECT ?, id, datetime('now', '-1 minute') FROM roles WHERE code = 'reviewer'
                """,
                (self.bob_id,),
            )
            conn.execute(
                "INSERT INTO user_role_assignments(user_id, role_id) SELECT ?, id FROM roles WHERE code = 'admin'",
                (self.alice_id,),
            )
            conn.commit()
        finally:
            conn.close()

        operator = self.authorization.user_context(self.bob_id)
        self.assertIn("learning:manage", operator["permissions"])
        self.assertNotIn("users:manage", operator["permissions"])
        self.assertNotIn("reviewer", operator["roles"])
        admin = self.authorization.user_context(self.alice_id)
        self.assertIn("users:manage", admin["permissions"])
        self.assertIn("audit:read", admin["permissions"])

        dependency = require_permission("users:manage")
        with patch(
            "app.api.v1.dependencies.authorization.get_authorization_service",
            return_value=AuthorizationService(SQLiteAuthorizationRepository(self.connection_factory)),
        ):
            authorized = dependency({"id": self.alice_id, "user_uid": "usr_alice"})
            self.assertIn("admin", authorized["roles"])
            with self.assertRaises(HTTPException) as forbidden:
                dependency({"id": self.bob_id, "user_uid": "usr_bob"})
        self.assertEqual(403, forbidden.exception.status_code)
        self.assertEqual("PERMISSION_DENIED", forbidden.exception.detail["code"])

    def test_audit_event_metadata_is_allowlisted_and_secrets_are_removed(self):
        audit_id = self.audit.record(
            "users.profile.updated",
            actor_user_id=self.alice_id,
            target_user_id=self.alice_id,
            resource_id="usr_alice",
            metadata={
                "changedFields": ["displayName", "bio"],
                "password": "NeverStoreThis",
                "refreshToken": "NeverStoreThisEither",
                "unexpected": "private-value",
            },
            ip_address="127.0.0.1",
            user_agent="users-test",
        )
        conn = self.connection_factory()
        try:
            row = conn.execute(
                "SELECT action, resource_type, resource_id, metadata_json FROM user_audit_logs WHERE id = ?",
                (audit_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual("users.profile.updated", row["action"])
        self.assertEqual(("profile", "usr_alice"), (row["resource_type"], row["resource_id"]))
        self.assertEqual({"changedFields": ["displayName", "bio"]}, json.loads(row["metadata_json"]))
        self.assertNotIn("NeverStoreThis", row["metadata_json"])
        with self.assertRaises(UsersError) as unknown:
            self.audit.record(
                "users.unknown",
                actor_user_id=self.alice_id,
                target_user_id=self.alice_id,
                resource_id="usr_alice",
            )
        self.assertEqual("AUDIT_EVENT_UNKNOWN", unknown.exception.code)

    def test_sensitive_user_command_writes_audit_with_request_context(self):
        request = Request(
            {
                "type": "http",
                "method": "PATCH",
                "path": "/api/v1/users/me/account",
                "headers": [(b"user-agent", b"audit-integration-test")],
                "client": ("127.0.0.1", 4321),
                "server": ("testserver", 80),
                "scheme": "http",
                "query_string": b"",
            }
        )
        current_user = {"id": self.alice_id, "user_uid": "usr_alice"}
        with (
            patch("app.api.v1.routers.users.get_account_service", return_value=self.accounts),
            patch("app.api.v1.routers.users.get_audit_service", return_value=self.audit),
        ):
            result = users_router.update_account(
                users_router.AccountUpdate(username="alice_audited"),
                request,
                current_user,
            )
        self.assertEqual("alice_audited", result["account"]["username"])
        conn = self.connection_factory()
        try:
            row = conn.execute(
                """
                SELECT action, resource_id, ip_address, user_agent, metadata_json
                FROM user_audit_logs
                WHERE actor_user_id = ? AND action = 'users.account.updated'
                """,
                (self.alice_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(("usr_alice", "127.0.0.1"), (row["resource_id"], row["ip_address"]))
        self.assertEqual("audit-integration-test", row["user_agent"])
        self.assertEqual({"changedFields": ["username"]}, json.loads(row["metadata_json"]))
        self.assertNotIn("alice_audited", row["metadata_json"])

    def test_account_contact_audit_records_fields_without_contact_values(self):
        request = Request(
            {
                "type": "http",
                "method": "PATCH",
                "path": "/api/v1/users/me/account",
                "headers": [(b"user-agent", b"contact-audit-test")],
                "client": ("127.0.0.1", 4321),
                "server": ("testserver", 80),
                "scheme": "http",
                "query_string": b"",
            }
        )
        current_user = {"id": self.alice_id, "user_uid": "usr_alice"}
        with (
            patch("app.api.v1.routers.users.get_account_service", return_value=self.accounts),
            patch("app.api.v1.routers.users.get_audit_service", return_value=self.audit),
        ):
            users_router.update_account(
                users_router.AccountUpdate(
                    email="audit@example.test",
                    phone="13800000002",
                    currentPassword="Current123",
                ),
                request,
                current_user,
            )
        conn = self.connection_factory()
        try:
            row = conn.execute(
                "SELECT metadata_json FROM user_audit_logs WHERE actor_user_id = ? AND action = 'users.account.updated' ORDER BY id DESC LIMIT 1",
                (self.alice_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual({"changedFields": ["email", "phone"]}, json.loads(row["metadata_json"]))
        self.assertNotIn("audit@example.test", row["metadata_json"])
        self.assertNotIn("13800000002", row["metadata_json"])

    def test_auth_register_login_current_refresh_and_logout(self):
        registered = self.auth.register(
            {
                "username": "charlie",
                "password": "Current123",
                "email": "Charlie@Example.Test",
                "displayName": "Charlie",
                "privacyAccepted": True,
            },
            self.context,
        )
        self.assertEqual("charlie", registered["user"]["username"])
        self.assertEqual("charlie@example.test", registered["user"]["email"])
        with self.assertRaises(UsersError) as duplicate:
            self.auth.register(
                {"username": "charlie", "password": "Current123", "email": None, "displayName": None, "privacyAccepted": True},
                self.context,
            )
        self.assertEqual("USERNAME_TAKEN", duplicate.exception.code)
        self.assertEqual(409, duplicate.exception.status_code)

        logged_in = self.auth.login({"identifier": "charlie", "password": "Current123", "deviceName": "browser", "privacyAccepted": True}, self.context)
        current = self.auth.current_user_from_token(logged_in["accessToken"])
        self.assertEqual("usr_", current["user_uid"][:4])
        refreshed = self.auth.refresh(logged_in["refreshToken"], self.context)
        self.assertEqual("Bearer", refreshed["tokenType"])
        self.assertIn("refreshToken", refreshed)
        self.assertNotEqual(logged_in["refreshToken"], refreshed["refreshToken"])
        self.auth.logout(
            current["id"],
            refreshed["refreshToken"],
            user_uid=current["user_uid"],
            context=self.context,
        )
        self.assertEqual(
            4,
            self.database_value(
                """
                SELECT COUNT(*) FROM user_audit_logs
                WHERE target_user_id = ? AND action IN (
                    'users.auth.registered', 'users.auth.login_succeeded',
                    'users.auth.session_refreshed', 'users.auth.session_logged_out'
                )
                """,
                (current["id"],),
            ),
        )
        with self.assertRaises(UsersError) as revoked:
            self.auth.refresh(refreshed["refreshToken"], self.context)
        self.assertEqual("REFRESH_TOKEN_INVALID", revoked.exception.code)

    def test_registration_accepts_optional_phone_and_phone_login_is_normalized(self):
        registered = self.auth.register(
            {
                "username": "phone_user",
                "password": "Current123",
                "email": None,
                "phone": "138 0000 0003",
                "displayName": "Phone User",
                "privacyAccepted": True,
            },
            self.context,
        )
        self.assertEqual("+8613800000003", registered["user"]["phone"])
        logged_in = self.auth.login(
            {
                "identifier": "138-0000-0003",
                "password": "Current123",
                "privacyAccepted": True,
                "deviceName": "phone-login",
            },
            self.context,
        )
        self.assertEqual("phone_user", logged_in["user"]["username"])
        with self.assertRaises(UsersError) as invalid_phone:
            self.auth.register(
                {
                    "username": "invalid_phone",
                    "password": "Current123",
                    "phone": "12345",
                    "privacyAccepted": True,
                },
                self.context,
            )
        self.assertEqual("PHONE_INVALID", invalid_phone.exception.code)

    def test_auth_requires_explicit_consent_and_login_can_regrant_revoked_policy(self):
        with self.assertRaises(UsersError) as missing_register_consent:
            self.auth.register(
                {"username": "no_consent", "password": "Current123", "email": None, "displayName": None},
                self.context,
            )
        self.assertEqual("PRIVACY_CONSENT_REQUIRED", missing_register_consent.exception.code)

        self.privacy.set_consent(
            self.alice_id,
            "privacy_policy",
            PRIVACY_POLICY_VERSION,
            False,
        )
        success_before = self.database_value(
            "SELECT COUNT(*) FROM user_login_logs WHERE user_id = ? AND result = 'success'",
            (self.alice_id,),
        )
        with self.assertRaises(UsersError) as missing_login_consent:
            self.auth.login(
                {"identifier": "alice", "password": "Current123", "deviceName": "browser"},
                self.context,
            )
        self.assertEqual("PRIVACY_CONSENT_REQUIRED", missing_login_consent.exception.code)
        self.assertEqual(
            success_before,
            self.database_value(
                "SELECT COUNT(*) FROM user_login_logs WHERE user_id = ? AND result = 'success'",
                (self.alice_id,),
            ),
        )

        logged_in = self.auth.login(
            {
                "identifier": "alice",
                "password": "Current123",
                "deviceName": "browser",
                "privacyAccepted": True,
            },
            self.context,
        )
        self.assertEqual("Bearer", logged_in["tokenType"])
        consent = next(
            item
            for item in self.privacy.consent_status(self.alice_id)["items"]
            if item["consentType"] == "privacy_policy"
        )
        self.assertEqual(("granted", "login"), (consent["status"], consent["source"]))
        self.assertEqual(
            success_before + 1,
            self.database_value(
                "SELECT COUNT(*) FROM user_login_logs WHERE user_id = ? AND result = 'success'",
                (self.alice_id,),
            ),
        )

    def test_remember_me_cookie_policy_survives_refresh_rotation(self):
        for remember_me in (False, True):
            logged_in = self.auth.login(
                {
                    "identifier": "alice",
                    "password": "Current123",
                    "deviceName": "browser",
                    "privacyAccepted": True,
                    "rememberMe": remember_me,
                },
                self.context,
            )
            rotated, persistent = self.auth.refresh_with_cookie_policy(logged_in["refreshToken"], self.context)
            self.assertEqual(remember_me, persistent)
            response = Response()
            auth_router._set_refresh_cookie(response, rotated["refreshToken"], persistent=persistent)
            cookie = response.headers.get("set-cookie", "")
            self.assertEqual(remember_me, "Max-Age=" in cookie)

    def test_auth_refresh_cookie_helpers_prefer_cookie_and_clear_cookie(self):
        login = self.auth.login({"identifier": "alice", "password": "Current123", "deviceName": "browser", "privacyAccepted": True}, self.context)
        response = Response()
        auth_router._set_refresh_cookie(response, login["refreshToken"])
        set_cookie = response.headers.get("set-cookie", "")
        self.assertIn("ai_nav_refresh_token=", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=lax", set_cookie)
        self.assertNotIn("Secure", set_cookie)

        chosen = auth_router._refresh_token_from(auth_router.RefreshRequest(refreshToken="body-refresh-token-123"), login["refreshToken"])
        self.assertEqual(login["refreshToken"], chosen)
        rotated = self.auth.refresh(chosen, self.context)
        self.assertIn("refreshToken", rotated)

        clear_response = Response()
        auth_router._clear_refresh_cookie(clear_response)
        clear_cookie = clear_response.headers.get("set-cookie", "")
        self.assertIn("ai_nav_refresh_token=", clear_cookie)
        self.assertIn("Max-Age=0", clear_cookie)

    def test_auth_refresh_rotation_replay_revokes_token_family(self):
        logged_in = self.auth.login({"identifier": "alice", "password": "Current123", "deviceName": "browser", "privacyAccepted": True}, self.context)
        rotated = self.auth.refresh(logged_in["refreshToken"], self.context)
        active_after_rotation = self.database_value(
            "SELECT COUNT(*) FROM user_sessions WHERE user_id = ? AND is_revoked = 0",
            (self.alice_id,),
        )
        self.assertEqual(2, active_after_rotation)
        with self.assertRaises(UsersError) as replay:
            self.auth.refresh(logged_in["refreshToken"], self.context)
        self.assertEqual("REFRESH_TOKEN_REPLAYED", replay.exception.code)
        self.assertEqual(401, replay.exception.status_code)
        self.assertEqual(
            0,
            self.database_value(
                """
                SELECT COUNT(*) FROM user_sessions
                WHERE user_id = ? AND is_revoked = 0
                  AND COALESCE(token_family_uid, session_uid) = (
                    SELECT COALESCE(token_family_uid, session_uid)
                    FROM user_sessions WHERE refresh_token_hash IS NOT NULL AND revoked_reason = 'rotated'
                    ORDER BY id DESC LIMIT 1
                  )
                """,
                (self.alice_id,),
            ),
        )
        with self.assertRaises(UsersError) as family_revoked:
            self.auth.refresh(rotated["refreshToken"], self.context)
        self.assertEqual("REFRESH_TOKEN_INVALID", family_revoked.exception.code)

    def test_auth_login_failure_records_stable_401(self):
        with self.assertRaises(UsersError) as invalid:
            self.auth.login({"identifier": "alice", "password": "wrongpass", "deviceName": "browser", "privacyAccepted": True}, self.context)
        self.assertEqual("INVALID_CREDENTIALS", invalid.exception.code)
        self.assertEqual(401, invalid.exception.status_code)
        self.assertEqual(1, self.database_value("SELECT failed_attempts FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,)))
        self.assertEqual(1, self.database_value("SELECT COUNT(*) FROM user_login_logs WHERE login_identifier = 'alice' AND result = 'failed'"))

        with self.assertRaises(UsersError) as missing:
            self.auth.login({"identifier": "missing-user", "password": "wrongpass", "deviceName": "browser", "privacyAccepted": True}, self.context)
        self.assertEqual((invalid.exception.code, invalid.exception.message, invalid.exception.status_code), (missing.exception.code, missing.exception.message, missing.exception.status_code))

    def test_auth_rate_limit_is_atomic_windowed_and_hashes_subjects(self):
        now = {"value": 1_800_000_000}
        limiter = AuthRateLimiter(
            SQLiteAuthRateLimitRepository(self.connection_factory),
            clock=lambda: now["value"],
        )
        subjects = {"ip": "198.51.100.24", "identifier": "Alice@Example.Test"}
        for _ in range(10):
            limiter.enforce("login", subjects)
        with self.assertRaises(UsersError) as blocked:
            limiter.enforce("login", subjects)
        self.assertEqual(("AUTH_RATE_LIMITED", 429), (blocked.exception.code, blocked.exception.status_code))
        self.assertGreater(blocked.exception.retry_after, 0)
        conn = self.connection_factory()
        try:
            rows = conn.execute("SELECT scope, subject_hash, request_count FROM user_auth_rate_limits").fetchall()
        finally:
            conn.close()
        serialized = json.dumps(rows)
        self.assertNotIn("alice", serialized.lower())
        self.assertNotIn("198.51.100.24", serialized)
        self.assertTrue(all(len(row["subject_hash"]) == 64 for row in rows))
        now["value"] += 301
        limiter.enforce("login", subjects)

    def test_forwarded_ip_is_used_only_for_trusted_proxy_chain(self):
        def request(client: str, forwarded: str) -> Request:
            return Request({
                "type": "http",
                "method": "POST",
                "path": "/api/v1/auth/login",
                "headers": [(b"x-forwarded-for", forwarded.encode("ascii"))],
                "client": (client, 1234),
                "server": ("testserver", 80),
                "scheme": "http",
                "query_string": b"",
            })

        spoofed = request("198.51.100.10", "203.0.113.20")
        self.assertEqual("198.51.100.10", auth_router._client_ip(spoofed, ("10.0.0.0/8",)))
        proxied = request("10.0.0.2", "203.0.113.20, 10.0.0.1")
        self.assertEqual("203.0.113.20", auth_router._client_ip(proxied, ("10.0.0.0/8",)))
        malformed = request("10.0.0.2", "not-an-ip")
        self.assertEqual("10.0.0.2", auth_router._client_ip(malformed, ("10.0.0.0/8",)))

    def test_rate_limit_http_boundary_returns_retry_after(self):
        class BlockedLimiter:
            @staticmethod
            def enforce(_operation, _subjects):
                error = UsersError("AUTH_RATE_LIMITED", "请求过于频繁，请稍后重试", 429)
                error.retry_after = 37
                raise error

        with patch("app.api.v1.routers.auth.get_auth_rate_limiter", return_value=BlockedLimiter()):
            with self.assertRaises(HTTPException) as blocked:
                auth_router._enforce_rate_limit("login", {"ip": "127.0.0.1"})
        self.assertEqual(429, blocked.exception.status_code)
        self.assertEqual("37", blocked.exception.headers["Retry-After"])
        self.assertEqual("AUTH_RATE_LIMITED", blocked.exception.detail["code"])

    def test_login_failures_temporarily_lock_without_revealing_account_state(self):
        for _ in range(5):
            with self.assertRaises(UsersError) as invalid:
                self.auth.login({"identifier": "alice", "password": "wrongpass", "deviceName": "browser", "privacyAccepted": True}, self.context)
            self.assertEqual("INVALID_CREDENTIALS", invalid.exception.code)

        self.assertEqual(5, self.database_value("SELECT failed_attempts FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,)))
        self.assertIsNotNone(self.database_value("SELECT locked_until FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,)))

        with self.assertRaises(UsersError) as locked:
            self.auth.login({"identifier": "alice", "password": "Current123", "deviceName": "browser", "privacyAccepted": True}, self.context)
        self.assertEqual("INVALID_CREDENTIALS", locked.exception.code)

        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute(
                "UPDATE user_auth_passwords SET locked_until = datetime('now', '-1 minute') WHERE user_id = ?",
                (self.alice_id,),
            )
            conn.commit()
        finally:
            conn.close()
        logged_in = self.auth.login({"identifier": "alice", "password": "Current123", "deviceName": "browser", "privacyAccepted": True}, self.context)
        self.assertEqual("Bearer", logged_in["tokenType"])
        self.assertEqual(0, self.database_value("SELECT failed_attempts FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,)))
        self.assertIsNone(self.database_value("SELECT locked_until FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,)))

    def test_successful_login_upgrades_legacy_password_hash(self):
        legacy_hash = hash_password("Current123", rounds=max(1, PASSWORD_HASH_ROUNDS - 1))
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("UPDATE user_auth_passwords SET password_hash = ? WHERE user_id = ?", (legacy_hash, self.alice_id))
            conn.commit()
        finally:
            conn.close()
        logged_in = self.auth.login({"identifier": "alice", "password": "Current123", "deviceName": "browser", "privacyAccepted": True}, self.context)
        self.assertEqual("Bearer", logged_in["tokenType"])
        upgraded_hash = self.database_value("SELECT password_hash FROM user_auth_passwords WHERE user_id = ?", (self.alice_id,))
        self.assertNotEqual(legacy_hash, upgraded_hash)
        self.assertIn(f"pbkdf2_sha256${PASSWORD_HASH_ROUNDS}$", upgraded_hash)

    def test_auth_security_reset_flow_revokes_sessions(self):
        self.security.replace_security_questions(
            self.alice_id,
            "Current123",
            [{"question": "城市?", "answer": "杭州"}],
        )
        started = self.auth.password_reset_security_start("alice", self.context)
        self.assertEqual(1, len(started["questions"]))
        with self.assertRaises(UsersError) as wrong_answer:
            self.auth.password_reset_security_verify(started["resetUid"], ["上海"])
        self.assertEqual("SECURITY_ANSWER_INVALID", wrong_answer.exception.code)
        verified = self.auth.password_reset_security_verify(started["resetUid"], ["杭州"], self.context)
        confirmed = self.auth.password_reset_security_confirm(verified["resetToken"], "Newpass123", self.context)
        self.assertEqual("ok", confirmed["status"])
        self.assertEqual(1, self.database_value("SELECT token_version FROM user_accounts WHERE id = ?", (self.alice_id,)))
        self.assertEqual(1, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual("password_reset", self.database_value("SELECT revoked_reason FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual(
            3,
            self.database_value(
                "SELECT COUNT(*) FROM user_audit_logs WHERE target_user_id = ? AND action LIKE 'users.auth.password_reset_%'",
                (self.alice_id,),
            ),
        )

    def test_password_update_revokes_user_sessions_and_uses_stable_401(self):
        with self.assertRaises(UsersError) as invalid:
            self.security.update_password(self.alice_id, "wrong-password", "Newpass123")
        self.assertEqual("CURRENT_PASSWORD_INVALID", invalid.exception.code)
        self.assertEqual(401, invalid.exception.status_code)
        result = self.security.update_password(self.alice_id, "Current123", "Newpass123")
        self.assertEqual("ok", result["status"])
        self.assertEqual(1, self.database_value("SELECT token_version FROM user_accounts WHERE id = ?", (self.alice_id,)))
        self.assertEqual(1, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual("password_changed", self.database_value("SELECT revoked_reason FROM user_sessions WHERE session_uid = 'sess_alice'"))
        self.assertEqual(0, self.database_value("SELECT is_revoked FROM user_sessions WHERE session_uid = 'sess_bob'"))

    def test_security_questions_are_hashed_and_duplicate_questions_fail(self):
        with self.assertRaises(UsersError) as duplicate:
            self.security.replace_security_questions(
                self.alice_id,
                "Current123",
                [{"question": "城市?", "answer": "杭州"}, {"question": "城市?", "answer": "上海"}],
            )
        self.assertEqual("SECURITY_QUESTION_DUPLICATE", duplicate.exception.code)
        result = self.security.replace_security_questions(
            self.alice_id,
            "Current123",
            [{"question": "城市?", "answer": "杭州"}],
        )
        self.assertTrue(result["configured"])
        stored_answer = self.database_value("SELECT answer_hash FROM user_security_questions WHERE user_id = ?", (self.alice_id,))
        self.assertNotEqual("杭州", stored_answer)

    def test_users_metrics_aggregate_without_pii_and_raise_threshold_alerts(self):
        metrics = UsersMetrics()
        for _ in range(5):
            metrics.record("auth.login", 401, "INVALID_CREDENTIALS")
        metrics.record("auth.login", 423, "ACCOUNT_LOCKED")
        metrics.record("auth.register", 201, None)
        snapshot = metrics.snapshot()
        self.assertFalse(snapshot["meta"]["containsPii"])
        self.assertEqual("users.observability", snapshot["meta"]["source"])
        self.assertIn("AUTH_LOGIN_FAILURE_SPIKE", {item["code"] for item in snapshot["alerts"]})
        self.assertIn("AUTH_ACCOUNT_LOCKED", {item["code"] for item in snapshot["alerts"]})
        serialized = json.dumps(snapshot)
        self.assertNotIn("username", serialized.lower())
        self.assertNotIn("token", serialized.lower())

    def test_request_ids_reject_log_injection_and_preserve_safe_values(self):
        self.assertEqual("client-request_123", request_id("client-request_123"))
        generated = request_id("bad\nrequest")
        self.assertRegex(generated, r"^[a-f0-9]{32}$")

    def test_production_runtime_security_rejects_unsafe_configuration(self):
        with self.assertRaisesRegex(RuntimeError, "AI_NAV_SECRET_KEY"):
            validate_runtime_security("production", DEV_SECRET_KEY, ("https://app.example.test",), True)
        with self.assertRaisesRegex(RuntimeError, "wildcard"):
            validate_runtime_security("development", DEV_SECRET_KEY, ("*",), False)
        with self.assertRaisesRegex(RuntimeError, "REFRESH_COOKIE_SECURE"):
            validate_runtime_security("production", "x" * 32, ("https://app.example.test",), False)
        validate_runtime_security("production", "x" * 32, ("https://app.example.test",), True)

    def test_liveness_and_database_readiness_are_separate(self):
        self.assertEqual({"status": "ok"}, health_live())
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO schema_migrations(version) VALUES ('001.sql')")
            self.assertEqual(
                {"status": "ready", "migrationCount": 1},
                check_database_ready(conn, {"001.sql"}),
            )
            with self.assertRaisesRegex(RuntimeError, "Missing migrations"):
                check_database_ready(conn, {"001.sql", "002.sql"})
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
