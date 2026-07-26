import importlib.util
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "provision-http-test-account.py"
SYNTHETIC_USERNAME = "synthetic_http_test_user"
SYNTHETIC_PASSWORD = "Synthetic" + "-Pass9!"


def load_script():
    os.environ["AI_NAV_DISABLE_DOTENV"] = "1"
    backend_path = str(ROOT / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    spec = importlib.util.spec_from_file_location("provision_http_test_account", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Provisioning script cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStdin:
    def __init__(self, interactive: bool):
        self._interactive = interactive

    def isatty(self):
        return self._interactive


class ProvisionHttpTestAccountTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = load_script()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.external_root = Path(self.temp.name).resolve()
        self.database_path = self.external_root / "database" / "http-test.sqlite3"
        self.upload_dir = self.external_root / "uploads"

    def tearDown(self):
        self.temp.cleanup()

    def provision(self, *, environment="http_test", username=SYNTHETIC_USERNAME):
        with (
            patch.object(self.script, "APP_ENV", environment),
            patch.object(self.script, "HTTP_TEST_ACCOUNT_USERNAME", SYNTHETIC_USERNAME),
        ):
            return self.script.provision_http_test_account(
                username,
                SYNTHETIC_PASSWORD,
                database_path=self.database_path,
                upload_dir=self.upload_dir,
            )

    def test_creates_one_account_without_active_refresh_session_or_secret_output(self):
        result = self.provision()

        with closing(sqlite3.connect(self.database_path)) as conn:
            account_count = conn.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0]
            active_sessions = conn.execute(
                "SELECT COUNT(*) FROM user_sessions WHERE is_revoked = 0"
            ).fetchone()[0]
            password_hash = conn.execute(
                "SELECT password_hash FROM user_auth_passwords"
            ).fetchone()[0]

        self.assertEqual(1, account_count)
        self.assertEqual(0, active_sessions)
        self.assertTrue(self.upload_dir.is_dir())
        self.assertEqual("created", result["status"])
        rendered = repr(result)
        for forbidden in (
            SYNTHETIC_USERNAME,
            SYNTHETIC_PASSWORD,
            password_hash,
            "accessToken",
            "refreshToken",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_allows_only_test_and_preview_profiles(self):
        for allowed in ("http_test", "provider_preview"):
            with self.subTest(environment=allowed):
                database_path = self.external_root / allowed / "account.sqlite3"
                upload_dir = self.external_root / allowed / "uploads"
                with (
                    patch.object(self.script, "APP_ENV", allowed),
                    patch.object(
                        self.script,
                        "HTTP_TEST_ACCOUNT_USERNAME",
                        SYNTHETIC_USERNAME,
                    ),
                ):
                    result = self.script.provision_http_test_account(
                        SYNTHETIC_USERNAME,
                        SYNTHETIC_PASSWORD,
                        database_path=database_path,
                        upload_dir=upload_dir,
                    )
                self.assertEqual("created", result["status"])

        for rejected in ("development", "test", "production"):
            with self.subTest(environment=rejected):
                with self.assertRaises(self.script.ProvisioningError):
                    self.provision(environment=rejected)

    def test_rejects_paths_inside_source_tree(self):
        internal_database = ROOT / ".task7-test-data" / "account.sqlite3"
        internal_uploads = ROOT / ".task7-test-data" / "uploads"
        with (
            patch.object(self.script, "APP_ENV", "http_test"),
            patch.object(
                self.script,
                "HTTP_TEST_ACCOUNT_USERNAME",
                SYNTHETIC_USERNAME,
            ),
        ):
            for database_path, upload_dir in (
                (internal_database, self.upload_dir),
                (self.database_path, internal_uploads),
            ):
                with self.subTest(database_path=database_path, upload_dir=upload_dir):
                    with self.assertRaises(self.script.ProvisioningError):
                        self.script.provision_http_test_account(
                            SYNTHETIC_USERNAME,
                            SYNTHETIC_PASSWORD,
                            database_path=database_path,
                            upload_dir=upload_dir,
                        )
        self.assertFalse((ROOT / ".task7-test-data").exists())

    def test_rejects_identifier_that_does_not_match_allowed_account(self):
        with (
            patch.object(self.script, "APP_ENV", "http_test"),
            patch.object(
                self.script,
                "HTTP_TEST_ACCOUNT_USERNAME",
                SYNTHETIC_USERNAME,
            ),
        ):
            with self.assertRaises(self.script.ProvisioningError) as raised:
                self.script.provision_http_test_account(
                    "different_synthetic_user",
                    SYNTHETIC_PASSWORD,
                    database_path=self.database_path,
                    upload_dir=self.upload_dir,
                )
        self.assertNotIn(SYNTHETIC_USERNAME, str(raised.exception))

    def test_rejects_second_run_or_database_containing_any_account(self):
        self.provision()

        with self.assertRaises(self.script.ProvisioningError):
            self.provision()

        with closing(sqlite3.connect(self.database_path)) as conn:
            self.assertEqual(
                1,
                conn.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0],
            )

    def test_failure_does_not_leave_half_initialized_account(self):
        with (
            patch.object(self.script, "APP_ENV", "http_test"),
            patch.object(
                self.script,
                "HTTP_TEST_ACCOUNT_USERNAME",
                SYNTHETIC_USERNAME,
            ),
            patch.object(
                self.script.AuthenticationService,
                "register",
                side_effect=RuntimeError("synthetic failure"),
            ),
        ):
            with self.assertRaises(self.script.ProvisioningError):
                self.script.provision_http_test_account(
                    SYNTHETIC_USERNAME,
                    SYNTHETIC_PASSWORD,
                    database_path=self.database_path,
                    upload_dir=self.upload_dir,
                )

        self.assertFalse(self.database_path.exists())
        self.assertFalse(self.upload_dir.exists())

    def test_cli_rejects_arguments_password_environment_and_piped_input(self):
        cases = (
            {
                "argv": ["--password", SYNTHETIC_PASSWORD],
                "environ": {},
                "stdin": FakeStdin(True),
            },
            {
                "argv": [],
                "environ": {
                    "AI_NAV_HTTP_TEST_ACCOUNT_PASSWORD": SYNTHETIC_PASSWORD,
                },
                "stdin": FakeStdin(True),
            },
            {
                "argv": [],
                "environ": {},
                "stdin": FakeStdin(False),
            },
        )
        for case in cases:
            with self.subTest(case=case):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch.dict(os.environ, case["environ"], clear=False),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    exit_code = self.script.main(
                        case["argv"],
                        stdin=case["stdin"],
                    )
                self.assertNotEqual(0, exit_code)
                rendered = stdout.getvalue() + stderr.getvalue()
                self.assertNotIn(SYNTHETIC_USERNAME, rendered)
                self.assertNotIn(SYNTHETIC_PASSWORD, rendered)


if __name__ == "__main__":
    unittest.main()
