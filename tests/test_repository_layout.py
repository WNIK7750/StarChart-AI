from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryLayoutTests(unittest.TestCase):
    def test_canonical_source_and_deployment_roots_exist(self) -> None:
        for relative_path in (
            "backend/app",
            "frontend/index.html",
            "database/migrations",
            "deploy/production/env.example",
            "docs/00-index/repository-layout.md",
            "scripts/verify-repository-layout.ps1",
        ):
            self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def test_retired_root_paths_are_absent(self) -> None:
        for retired_path in (
            "frontend - 副本",
            "full-stack-analysis",
            "production.env.example",
        ):
            self.assertFalse((ROOT / retired_path).exists(), retired_path)

    def test_migrations_are_contiguous_and_uniquely_numbered(self) -> None:
        names = sorted(path.name for path in (ROOT / "database/migrations").glob("*.sql"))
        numbers = []
        for name in names:
            match = re.fullmatch(r"(\d{3})_[a-z0-9_]+\.sql", name)
            self.assertIsNotNone(match, name)
            numbers.append(int(match.group(1)))
        self.assertEqual(list(range(1, len(numbers) + 1)), numbers)

    def test_historical_analysis_is_marked_as_snapshot(self) -> None:
        readme = (
            ROOT
            / "docs/05-quality/analysis/2026-08-02-full-stack-snapshot/README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("历史快照", readme)
        self.assertIn("不得作为当前运行或发布依据", readme)

    def test_agent_gate_uses_only_the_test_support_provider(self) -> None:
        script = (ROOT / "scripts/verify-agent.ps1").read_text(encoding="utf-8")
        self.assertNotIn("backend/app/agent/providers/fake.py", script)
        self.assertIn("tests/support/fake_provider.py", script)
        self.assertFalse((ROOT / "backend/app/agent/providers/fake.py").exists())
        self.assertTrue((ROOT / "tests/support/fake_provider.py").is_file())


if __name__ == "__main__":
    unittest.main()
