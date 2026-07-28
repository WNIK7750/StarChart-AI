from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build-http-test-server-validation.py"


def safe_snapshot() -> dict:
    return {
        "targetCommit": "0" * 40,
        "archiveSha256": "1" * 64,
        "authReportSha256": "2" * 64,
        "server": {
            "nginxActive": True,
            "nginxSyntaxValid": True,
            "httpTestServiceActive": True,
            "deterministicSmokePassed": True,
            "portBindings": {
                "legacy8000": "0.0.0.0",
                "httpTest8001": "127.0.0.1",
                "providerPreview8002": "closed",
            },
            "database": {
                "accountCount": 1,
                "mode": "0600",
                "owner": "dedicated-http-test-service-account",
                "isolatedFromLegacyDatabase": True,
            },
            "backup": {
                "archivePresent": True,
                "gzipIntegrityPassed": True,
                "restoreExercise": "not_run",
            },
        },
        "publicRoutes": [
            {
                "path": "/",
                "statusCode": 200,
                "elapsedMs": 1.25,
                "downloadBytes": 10,
            }
        ],
        "runtimePolicy": {
            "deploymentProfile": "http_test",
            "publicBasePath": "/StarChart-AI",
            "registration": False,
            "recovery": False,
            "identityChanges": False,
            "privacyWrites": False,
            "guestChat": True,
            "authenticatedSessions": True,
        },
    }


def safe_auth_report() -> dict:
    return {
        "schemaVersion": 1,
        "validationStatus": "passed",
        "checksRecorded": 1,
        "passedChecks": 1,
        "failedChecks": 0,
        "checks": {
            "login": {
                "passed": True,
                "statusCode": 200,
                "elapsedMs": 3.5,
                "errorType": None,
            }
        },
        "sensitiveDataRecorded": False,
    }


class HttpTestServerValidationBuilderTests(unittest.TestCase):
    def run_builder(
        self,
        snapshot: dict,
        auth_report: dict,
    ) -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        snapshot_path = root / "snapshot.json"
        auth_path = root / "auth.json"
        output = root / "validation.json"
        snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
        auth_path.write_text(json.dumps(auth_report), encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--snapshot",
                str(snapshot_path),
                "--auth-report",
                str(auth_path),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return process, output, temp

    def test_builder_emits_redacted_server_validation_contract(self):
        process, output, temp = self.run_builder(
            safe_snapshot(),
            safe_auth_report(),
        )
        with temp:
            self.assertEqual(0, process.returncode, process.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("go", payload["conclusions"]["httpTestDeployment"])
            self.assertEqual("no_go", payload["conclusions"]["productionRelease"])
            self.assertEqual(1, payload["authenticatedFlow"]["passedChecks"])
            self.assertFalse(payload["containsSecrets"])
            rendered = json.dumps(payload).lower()
            for forbidden in (
                "username",
                "password",
                "token",
                "cookie",
                "requestbody",
                "responsebody",
                "hostaddress",
            ):
                self.assertNotIn(forbidden, rendered)

    def test_builder_rejects_extra_sensitive_auth_fields_without_replacing_output(self):
        auth_report = safe_auth_report()
        auth_report["username"] = "synthetic-should-be-rejected"
        process, output, temp = self.run_builder(safe_snapshot(), auth_report)
        with temp:
            self.assertNotEqual(0, process.returncode)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
