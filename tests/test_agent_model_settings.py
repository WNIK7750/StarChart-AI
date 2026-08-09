import unittest
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app.agent.factory import build_user_agent_loop
from app.db.database import apply_migrations
from app.users.audit.events import AUDIT_EVENTS
from app.users.command_safety import COMMAND_SAFETY
from app.users.common import UsersError
from app.users.model_settings.service import AgentModelSettingsService, ResolvedAgentModelSettings


class MemoryRepository:
    def __init__(self):
        self.row = None

    def get(self, _user_id):
        return dict(self.row) if self.row else None

    def upsert(self, _user_id, values, expected_version):
        if self.row is None:
            if expected_version is not None:
                return None, False
            version = 1
        else:
            if expected_version != self.row["version"]:
                return dict(self.row), False
            version = self.row["version"] + 1
        self.row = {**values, "version": version}
        return dict(self.row), True

    def delete(self, _user_id):
        existed = self.row is not None
        self.row = None
        return existed


class MemoryCredentialStore:
    def __init__(self):
        self.secrets = {}

    def get(self, subject):
        return self.secrets.get(subject)

    def put(self, subject, secret):
        self.secrets[subject] = secret

    def delete(self, subject):
        return self.secrets.pop(subject, None) is not None


class AgentModelSettingsServiceTest(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryRepository()
        self.credentials = MemoryCredentialStore()
        self.service = AgentModelSettingsService(
            self.repository,
            self.credentials,
            allowed_hosts=("dashscope.aliyuncs.com",),
        )
        self.subject = "usr_test"

    def payload(self, **changes):
        return {
            "expectedVersion": None,
            "providerKey": "dashscope",
            "providerName": "阿里云百炼 / DashScope",
            "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "modelDisplayName": "Qwen Test",
            "modelId": "qwen-test",
            "apiKey": "sk-user-secret",
            "maxOutputTokens": 1200,
            "enabled": True,
            **changes,
        }

    def test_secret_is_stored_outside_database_and_never_returned(self):
        result = self.service.save(7, self.subject, self.payload())
        self.assertNotIn("apiKey", self.repository.row)
        self.assertFalse(any(
            "api" in name.lower() and "key" in name.lower()
            for name in self.repository.row
        ))
        self.assertEqual("sk-user-secret", self.credentials.get(self.subject))
        self.assertTrue(result["model"]["hasApiKey"])
        self.assertNotIn("apiKey", result["model"])
        resolved = self.service.resolve(7, self.subject)
        self.assertEqual("sk-user-secret", resolved.api_key)
        self.assertEqual("Qwen Test", resolved.model_display_name)
        self.assertEqual("qwen-test", resolved.model_id)

    def test_provider_default_output_limit_is_preserved_as_none(self):
        result = self.service.save(7, self.subject, self.payload(maxOutputTokens=None))
        self.assertIsNone(result["model"]["maxOutputTokens"])
        self.assertIsNone(self.service.resolve(7, self.subject).max_output_tokens)

    def test_blank_secret_preserves_existing_credential(self):
        first = self.service.save(7, self.subject, self.payload())
        self.service.save(7, self.subject, self.payload(
            expectedVersion=first["model"]["version"], apiKey=None, modelId="qwen-next"
        ))
        self.assertEqual("sk-user-secret", self.credentials.get(self.subject))
        self.assertEqual("needs_retest", self.repository.row["connectionStatus"])

    def test_version_conflict_restores_previous_credential(self):
        first = self.service.save(7, self.subject, self.payload())
        with self.assertRaises(UsersError) as raised:
            self.service.save(7, self.subject, self.payload(
                expectedVersion=first["model"]["version"] + 10,
                apiKey="sk-replacement",
            ))
        self.assertEqual("AGENT_MODEL_VERSION_CONFLICT", raised.exception.code)
        self.assertEqual("sk-user-secret", self.credentials.get(self.subject))

    def test_delete_removes_metadata_and_external_credential(self):
        self.service.save(7, self.subject, self.payload())
        self.service.delete(7, self.subject)
        self.assertIsNone(self.repository.row)
        self.assertIsNone(self.credentials.get(self.subject))

    def test_private_or_unapproved_model_hosts_are_blocked(self):
        for url, code in (
            ("http://dashscope.aliyuncs.com/v1", "AGENT_MODEL_BASE_URL_INVALID"),
            ("https://127.0.0.1/v1", "AGENT_MODEL_HOST_BLOCKED"),
            ("https://example.com/v1", "AGENT_MODEL_HOST_NOT_ALLOWED"),
        ):
            with self.subTest(url=url), self.assertRaises(UsersError) as raised:
                self.service.save(7, self.subject, self.payload(baseUrl=url))
            self.assertEqual(code, raised.exception.code)


class AgentModelCredentialMigrationTest(unittest.TestCase):
    def test_final_database_schema_contains_no_model_credential_column(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            database_path = Path(folder) / "agent-model.sqlite3"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.executescript((root / "database" / "schema.sql").read_text(encoding="utf-8"))
                apply_migrations(connection, root / "database" / "migrations")
                columns = {
                    row[1]: (row[3], row[4])
                    for row in connection.execute(
                        "PRAGMA table_info(user_agent_model_settings)"
                    ).fetchall()
                }
        self.assertNotIn("api_key", " ".join(sorted(columns)).lower())
        self.assertNotIn("cipher", " ".join(sorted(columns)).lower())
        self.assertIn("provider_key", columns)
        self.assertIn("model_display_name", columns)
        self.assertEqual((0, None), columns["max_output_tokens"])


class UserAgentModelRuntimeTest(unittest.TestCase):
    @patch("app.agent.factory.SiteAgentLoopRuntime", side_effect=lambda **kwargs: kwargs)
    @patch("app.agent.factory.ChatOpenAI", side_effect=lambda **kwargs: kwargs)
    def test_provider_default_does_not_send_max_tokens(self, chat_model, _runtime):
        runtime = build_user_agent_loop(ResolvedAgentModelSettings(
            provider_name="自定义提供商",
            base_url="https://api.openai.com/v1",
            model_display_name="我的模型",
            model_id="provider-model-id",
            api_key="secret",
            max_output_tokens=None,
        ))
        self.assertNotIn("max_tokens", chat_model.call_args.kwargs)
        self.assertEqual("provider-model-id", chat_model.call_args.kwargs["model"])
        self.assertEqual("我的模型", runtime["model_name"])


class AgentModelAuditContractTest(unittest.TestCase):
    def test_model_commands_have_registered_audit_and_safety_contracts(self):
        expected = {
            ("PUT", "/api/v1/users/me/agent-model"): "users.agent_model.updated",
            ("POST", "/api/v1/users/me/agent-model/test"): "users.agent_model.connection_tested",
            ("DELETE", "/api/v1/users/me/agent-model"): "users.agent_model.deleted",
        }
        for command, event in expected.items():
            with self.subTest(command=command):
                self.assertIn(event, AUDIT_EVENTS)
                self.assertEqual(event, COMMAND_SAFETY[command].audit)
