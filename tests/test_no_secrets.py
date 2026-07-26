from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNER_PATH = ROOT / "scripts" / "check-no-secrets.py"


def load_scanner():
    spec = importlib.util.spec_from_file_location("check_no_secrets", SCANNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("scanner module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NoSecretsScannerTests(unittest.TestCase):
    def test_scanner_reports_rule_and_location_without_echoing_secret_values(self):
        scanner = load_scanner()
        synthetic_private = "-----BEGIN " + "PRIVATE KEY-----"
        synthetic_bearer = "Bearer " + "synthetic-test-only-token-123456"
        synthetic_provider = "sk-" + "synthetic-test-only-provider-key-1234567890"
        synthetic_cookie = "Cookie: session=" + "synthetic-test-only-cookie"
        synthetic_assignment = (
            "OPENAI_API_" + "KEY=synthetic-test-only-environment-secret"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "synthetic-fixture.txt"
            fixture.write_text(
                "\n".join(
                    (
                        synthetic_private,
                        f"Authorization: {synthetic_bearer}",
                        synthetic_cookie,
                        synthetic_provider,
                        synthetic_assignment,
                    )
                ),
                encoding="utf-8",
            )

            findings = scanner.scan_paths([fixture], allowed_root=root)
            rendered = "\n".join(scanner.format_finding(item, root) for item in findings)

            self.assertIn("PRIVATE_KEY_HEADER", rendered)
            self.assertIn("BEARER_TOKEN", rendered)
            self.assertIn("COOKIE_VALUE", rendered)
            self.assertIn("PROVIDER_API_KEY", rendered)
            self.assertIn("SENSITIVE_ASSIGNMENT", rendered)
            self.assertIn("synthetic-fixture.txt:1:", rendered)
            for value in (
                synthetic_bearer,
                synthetic_provider,
                synthetic_cookie,
                synthetic_assignment,
            ):
                self.assertNotIn(value, rendered)

    def test_empty_and_test_placeholder_env_example_values_are_allowed(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            example = root / "service.env.example"
            example.write_text(
                "\n".join(
                    (
                        "OPENAI_API_KEY=",
                        "COOKIE_SECRET=synthetic-test-only-placeholder",
                        "PASSWORD=<set-at-deploy-time>",
                    )
                ),
                encoding="utf-8",
            )

            self.assertEqual([], scanner.scan_paths([example], allowed_root=root))

    def test_source_rule_fragments_without_secret_values_are_not_findings(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "synthetic_fixture.py"
            source.write_text(
                'synthetic_cookie = "Cookie: session=" + supplied_value\n',
                encoding="utf-8",
            )

            self.assertEqual([], scanner.scan_paths([source], allowed_root=root))

    def test_file_and_directory_inputs_report_forbidden_artifact_types_without_reading_them(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uploads = root / "uploads"
            uploads.mkdir()
            (uploads / "photo.txt").write_text("safe text", encoding="utf-8")
            database = root / "state.sqlite3"
            database.write_bytes(b"not-a-real-database")
            binary = root / "artifact.bin"
            binary.write_bytes(b"\x00synthetic")
            oversized = root / "large.txt"
            oversized.write_bytes(b"x" * (scanner.MAX_FILE_BYTES + 1))
            real_env = root / ".env"
            real_env.write_bytes(b"must-not-be-read")

            findings = scanner.scan_paths(
                [uploads, database, binary, oversized, real_env],
                allowed_root=root,
            )
            rules = {finding.rule for finding in findings}

            self.assertIn("UPLOAD_ARTIFACT", rules)
            self.assertIn("DATABASE_ARTIFACT", rules)
            self.assertIn("BINARY_ARTIFACT", rules)
            self.assertIn("OVERSIZED_FILE", rules)
            self.assertIn("SENSITIVE_ENV_FILE", rules)

    def test_paths_outside_the_explicit_scan_root_are_rejected_without_reading(self):
        scanner = load_scanner()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "allowed"
            allowed.mkdir()
            outside = root / "outside.txt"
            outside.write_text("safe", encoding="utf-8")

            findings = scanner.scan_paths([outside], allowed_root=allowed)

            self.assertEqual(["OUTSIDE_SCAN_ROOT"], [item.rule for item in findings])


if __name__ == "__main__":
    unittest.main()
