from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-release-package.ps1"
POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)


class ReleaseHttpTestOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.root / "scripts" / SCRIPT.name)
        shutil.copy2(
            ROOT / "scripts" / "check-no-secrets.py",
            self.root / "scripts" / "check-no-secrets.py",
        )
        self._write("scripts/provision-http-test-account.py", "print('provision')\n")
        self._write("backend/run.py", "print('release fixture')\n")
        self._write("deploy/http-test/env.example", "AI_NAV_SECRET_KEY=\n")
        self._write(
            "deploy/http-test/provider-preview.env.example",
            "AI_NAV_AGENT_PROVIDER_API_KEY=\n",
        )
        self._write("deploy/http-test/nginx/ai-nav.conf", "server {}\n")
        self._write("frontend/index.html", "<!doctype html>\n")
        self._write("production.env.example", "AI_NAV_SECRET_KEY=\n")
        self._write("README.md", "# Fixture\n")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write(self, relative_path: str, content: str = "fixture\n") -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(POWERSHELL),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.root / "scripts" / SCRIPT.name),
                "-PythonExecutable",
                sys.executable,
                *arguments,
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def _build_archive(self) -> Path:
        archive = self.root / "release.zip"
        result = self._run("-OutputPath", archive.name)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return archive

    def test_validate_only_counts_the_deployment_overlay_without_disclosing_content(
        self,
    ) -> None:
        result = self._run("-ValidateOnly")

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        summary = json.loads(result.stdout)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["deploymentOverlayCount"], 3)
        self.assertNotIn("AI_NAV_SECRET_KEY", result.stdout)
        self.assertNotIn("AI_NAV_AGENT_PROVIDER_API_KEY", result.stdout)

    def test_archive_contains_overlay_and_only_environment_templates(self) -> None:
        self._write("frontend/public.env.example", "PUBLIC_PLACEHOLDER=\n")
        archive = self._build_archive()

        with zipfile.ZipFile(archive) as package:
            members = {name.replace("\\", "/") for name in package.namelist()}

        self.assertIn("deploy/http-test/env.example", members)
        self.assertIn("deploy/http-test/provider-preview.env.example", members)
        self.assertIn("deploy/http-test/nginx/ai-nav.conf", members)
        self.assertIn("frontend/public.env.example", members)
        self.assertIn("scripts/provision-http-test-account.py", members)
        self.assertIn("scripts/check-no-secrets.py", members)
        environment_members = [
            name
            for name in members
            if Path(name).name == ".env" or ".env." in Path(name).name
        ]
        self.assertTrue(environment_members)
        self.assertTrue(
            all(
                Path(name).name == "env.example"
                or Path(name).name.endswith(".env.example")
                for name in environment_members
            )
        )

    def test_archive_normalizes_shell_scripts_to_lf_for_linux(self) -> None:
        shell_script = self.root / "deploy/http-test/scripts/install-overlay.sh"
        shell_script.parent.mkdir(parents=True, exist_ok=True)
        shell_script.write_bytes(b"#!/usr/bin/env bash\r\nset -euo pipefail\r\n")
        archive = self._build_archive()

        with zipfile.ZipFile(archive) as package:
            script = package.read("deploy/http-test/scripts/install-overlay.sh")

        self.assertEqual(script, b"#!/usr/bin/env bash\nset -euo pipefail\n")
        self.assertNotIn(b"\r", script)

    def test_forbidden_release_artifacts_fail_closed(self) -> None:
        forbidden_artifacts = {
            "frontend/runtime.env": "SECRET=not-a-real-secret\n",
            "frontend/runtime.sqlite3": "sqlite fixture\n",
            "frontend/uploads/payload.bin": "upload fixture\n",
            "frontend/database-backup.sql": "backup fixture\n",
            "frontend/application.log": "log fixture\n",
            "frontend/systemd/private.env": "SECRET=not-a-real-secret\n",
            "frontend/provider-response-evidence.json": "{}\n",
        }

        for relative_path, content in forbidden_artifacts.items():
            with self.subTest(relative_path=relative_path):
                artifact = self._write(relative_path, content)
                result = self._run("-ValidateOnly")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("forbidden", (result.stderr + result.stdout).lower())
                artifact.unlink()

    def test_archive_excludes_user_temp_git_and_test_artifacts_and_has_safe_names(
        self,
    ) -> None:
        self._write(".tmp_ci.txt")
        self._write(".tmp_push_ci.txt")
        self._write(".git/config")
        self._write("test-results/result.xml")
        archive = self._build_archive()

        with zipfile.ZipFile(archive) as package:
            members = [name.replace("\\", "/") for name in package.namelist()]

        self.assertFalse(any(".tmp_ci.txt" in name for name in members))
        self.assertFalse(any(".tmp_push_ci.txt" in name for name in members))
        self.assertFalse(any("/.git/" in f"/{name}" for name in members))
        self.assertFalse(any("test-results" in name for name in members))
        self.assertTrue(all(not Path(name).is_absolute() for name in members))
        self.assertTrue(all(":" not in name for name in members))
        self.assertTrue(all(str(self.root).replace("\\", "/") not in name for name in members))

    def test_selected_member_with_provider_key_shape_fails_redacted(self) -> None:
        synthetic_value = "sk-" + ("syntheticfixturevalue" * 2)
        self._write("backend/run.py", f'VALUE = "{synthetic_value}"\n')

        result = self._run("-ValidateOnly")

        self.assertNotEqual(result.returncode, 0)
        combined = result.stdout + result.stderr
        self.assertIn("PROVIDER_API_KEY", combined)
        self.assertNotIn(synthetic_value, combined)

    def test_builder_scans_exact_selected_and_staged_member_sets(self) -> None:
        script = (self.root / "scripts" / SCRIPT.name).read_text(encoding="utf-8")
        self.assertIn("Invoke-ReleaseSecretScan -ScanRoot $root -SelectedFiles $files", script)
        self.assertIn("$stagedFiles = @(Get-ChildItem -LiteralPath $stageRoot -Recurse -File)", script)
        self.assertIn(
            "Invoke-ReleaseSecretScan -ScanRoot $stageRoot -SelectedFiles $stagedFiles",
            script,
        )


if __name__ == "__main__":
    unittest.main()
