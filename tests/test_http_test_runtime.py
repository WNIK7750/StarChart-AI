import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.core.config import (
    DEV_SECRET_KEY,
    normalize_public_base_path,
    validate_runtime_security,
)


ROOT = Path(__file__).resolve().parents[1]


def safe_runtime(**overrides):
    """Return a hand-checked profile fixture with isolated persistence."""
    values = {
        "environment": "http_test",
        "secret_key": "s" * 32,
        "cors_origins": ("http://47.100.94.1",),
        "refresh_cookie_secure": False,
        "reset_database_on_start": False,
        "database_path": Path(tempfile.gettempdir()) / "ai-nav-http-test.sqlite3",
        "upload_dir": Path(tempfile.gettempdir()) / "ai-nav-http-test-uploads",
        "base_dir": ROOT,
        "refresh_cookie_samesite": "lax",
        "public_base_path": "/StarChart-AI",
        "http_test_account_username": "fixture-http-user",
        "agent_provider": "deterministic",
        "agent_provider_live_enabled": False,
        "app_host": "127.0.0.1",
        "app_port": 8001,
    }
    values.update(overrides)
    return values


def preview_environment(temp_root: Path, **overrides) -> dict[str, str]:
    database_path = temp_root / "preview.sqlite3"
    sqlite3.connect(database_path).close()
    values = {
        "PYTHONPATH": str(ROOT / "backend"),
        "AI_NAV_DISABLE_DOTENV": "1",
        "AI_NAV_ENV": "provider_preview",
        "AI_NAV_SECRET_KEY": "p" * 32,
        "AI_NAV_DATABASE_PATH": str(database_path),
        "AI_NAV_UPLOAD_DIR": str(temp_root / "preview-uploads"),
        "AI_NAV_CORS_ALLOW_ORIGINS": "https://preview.example.test",
        "AI_NAV_REFRESH_COOKIE_SECURE": "1",
        "AI_NAV_REFRESH_COOKIE_SAMESITE": "lax",
        "AI_NAV_API_WORKERS": "1",
        "AI_NAV_AGENT_RUNTIME_STATE_BACKEND": "process_local",
        "AI_NAV_APP_HOST": "127.0.0.1",
        "AI_NAV_APP_PORT": "8002",
        "AI_NAV_AGENT_PROVIDER": "openai_compatible",
        "AI_NAV_AGENT_PROVIDER_BASE_URL": "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        "AI_NAV_AGENT_PROVIDER_MODEL": "qwen3.5-flash",
        "AI_NAV_AGENT_PROVIDER_API_KEY": "fixture-provider-key",
        "AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS": "workspace.cn-beijing.maas.aliyuncs.com",
        "AI_NAV_AGENT_PROVIDER_LIVE_ENABLED": "1",
        "RESET_DATABASE_ON_START": "0",
    }
    values.update(overrides)
    return values


class HttpTestRuntimeTest(unittest.TestCase):
    def test_http_test_accepts_explicit_http_origin_and_external_storage(self):
        validate_runtime_security(**safe_runtime())

    def test_http_test_rejects_relaxations_that_would_break_the_isolated_contract(self):
        cases = (
            ({"secret_key": DEV_SECRET_KEY}, "non-default"),
            ({"secret_key": "short"}, "at least 32"),
            ({"database_path": ROOT / "database" / "http-test.sqlite3"}, "AI_NAV_DATABASE_PATH"),
            ({"upload_dir": ROOT / "uploads"}, "AI_NAV_UPLOAD_DIR"),
            ({"reset_database_on_start": True}, "RESET_DATABASE_ON_START"),
            ({"http_test_account_username": ""}, "HTTP_TEST_ACCOUNT_USERNAME"),
            ({"public_base_path": "/different-prefix"}, "PUBLIC_BASE_PATH"),
            ({"agent_provider": "openai_compatible"}, "deterministic"),
            ({"agent_provider_live_enabled": True}, "live Provider"),
        )
        for overrides, message in cases:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(RuntimeError, message):
                validate_runtime_security(**safe_runtime(**overrides))

    def test_normalize_public_base_path_returns_canonical_relative_prefix(self):
        for value, expected in (("", ""), ("/StarChart-AI/", "/StarChart-AI")):
            with self.subTest(value=value):
                self.assertEqual(expected, normalize_public_base_path(value))

    def test_normalize_public_base_path_rejects_non_path_input(self):
        for value in (
            "https://example.test/StarChart-AI",
            "//example.test/StarChart-AI",
            "/StarChart-AI\\child",
            "/StarChart-AI/../admin",
            "/StarChart-AI?debug=1",
            "/StarChart-AI#fragment",
        ):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                normalize_public_base_path(value)

    def test_provider_preview_rejects_unsafe_runtime_configuration(self):
        cases = (
            ({"AI_NAV_APP_HOST": "0.0.0.0"}, "APP_HOST"),
            ({"AI_NAV_APP_PORT": "70000"}, "APP_PORT"),
            (
                {
                    "AI_NAV_AGENT_PROVIDER": "deterministic",
                    "AI_NAV_AGENT_PROVIDER_LIVE_ENABLED": "0",
                },
                "openai_compatible",
            ),
            ({"AI_NAV_AGENT_PROVIDER_BASE_URL": "http://workspace.cn-beijing.maas.aliyuncs.com/v1"}, "must use HTTPS"),
            ({"AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS": ""}, "explicitly listed"),
            ({"AI_NAV_AGENT_PER_REQUEST_COST_CNY": "0"}, "finite positive"),
            ({"AI_NAV_DATABASE_PATH": str(ROOT / "database" / "preview.sqlite3")}, "AI_NAV_DATABASE_PATH"),
        )
        for overrides, message in cases:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as temp_dir:
                # A subprocess exercises the import boundary without any dotenv file.
                process = subprocess.run(
                    [sys.executable, "-c", "import app.core.config"],
                    cwd=ROOT,
                    env=preview_environment(Path(temp_dir), **overrides),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertNotEqual(0, process.returncode)
                self.assertIn(message, process.stderr)

    def test_provider_preview_allows_a_non_default_valid_port(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            process = subprocess.run(
                [sys.executable, "-c", "import app.core.config"],
                cwd=ROOT,
                env=preview_environment(Path(temp_dir), AI_NAV_APP_PORT="8012"),
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(0, process.returncode)
        self.assertEqual("", process.stdout)
        self.assertEqual("", process.stderr)
