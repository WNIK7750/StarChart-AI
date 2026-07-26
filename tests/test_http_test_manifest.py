from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build-http-test-deployment-manifest.py"
CHECK_NAMES = (
    "runtime",
    "policy",
    "agentHistory",
    "guestAgent",
    "frontend",
    "overlay",
    "release",
)
EXTERNAL_NAMES = (
    "serverDeployment",
    "providerPreview",
    "https",
    "backupRestore",
    "rollback",
)


def write_results(
    directory: Path,
    run_id: str,
    *,
    failed: str | None = None,
    mismatched_run: str | None = None,
) -> None:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for index, name in enumerate(CHECK_NAMES, start=1):
        payload = {
            "schemaVersion": 1,
            "runId": "stale-run" if name == mismatched_run else run_id,
            "name": name,
            "passed": name != failed,
            "count": index,
            "startedAt": timestamp,
            "finishedAt": timestamp,
        }
        (directory / f"{name}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )


class HttpTestManifestTests(unittest.TestCase):
    def run_builder(
        self,
        results: Path,
        output: Path,
        run_id: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--results-dir",
                str(results),
                "--run-id",
                run_id,
                "--output",
                str(output),
                "--source-commit",
                "WORKTREE",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_builder_emits_the_fixed_content_free_manifest_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            results = directory / "results"
            results.mkdir()
            output = directory / "manifest.json"
            write_results(results, "current-run")

            process = self.run_builder(results, output, "current-run")

            self.assertEqual(0, process.returncode, process.stderr)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(1, manifest["schemaVersion"])
            self.assertRegex(
                manifest["generatedAt"],
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            )
            self.assertEqual("WORKTREE", manifest["sourceCommit"])
            self.assertEqual(
                list(CHECK_NAMES),
                [check["name"] for check in manifest["checks"]],
            )
            self.assertEqual(
                list(range(1, 8)),
                [check["count"] for check in manifest["checks"]],
            )
            self.assertTrue(all(check["passed"] for check in manifest["checks"]))
            self.assertEqual(
                {name: "not_run" for name in EXTERNAL_NAMES},
                manifest["externalValidation"],
            )
            self.assertFalse(manifest["containsSecrets"])
            rendered = json.dumps(manifest)
            self.assertNotIn("current-run", rendered)
            self.assertNotIn(str(ROOT), rendered)
            self.assertNotRegex(rendered, r"(?i)(api[_-]?key|password|account)")

    def test_builder_rejects_results_from_another_run(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            results = directory / "results"
            results.mkdir()
            output = directory / "manifest.json"
            write_results(results, "current-run", mismatched_run="frontend")

            process = self.run_builder(results, output, "current-run")

            self.assertNotEqual(0, process.returncode)
            self.assertFalse(output.exists())

    def test_failed_check_does_not_replace_last_passing_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            results = directory / "results"
            results.mkdir()
            output = directory / "manifest.json"
            previous = '{"previousPassingEvidence":true}\n'
            output.write_text(previous, encoding="utf-8")
            write_results(results, "current-run", failed="release")

            process = self.run_builder(results, output, "current-run")

            self.assertNotEqual(0, process.returncode)
            self.assertEqual(previous, output.read_text(encoding="utf-8"))

    def test_builder_rejects_negative_or_non_integer_counts(self):
        for invalid_count in (-1, 1.5, True):
            with self.subTest(invalid_count=invalid_count):
                with tempfile.TemporaryDirectory() as temp:
                    directory = Path(temp)
                    results = directory / "results"
                    results.mkdir()
                    output = directory / "manifest.json"
                    write_results(results, "current-run")
                    path = results / "runtime.json"
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    payload["count"] = invalid_count
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    process = self.run_builder(results, output, "current-run")

                    self.assertNotEqual(0, process.returncode)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
