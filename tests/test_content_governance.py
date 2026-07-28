import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db.database import apply_migrations


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-content-links.py"
SPEC = importlib.util.spec_from_file_location("check_content_links", SCRIPT)
CONTENT_LINKS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(CONTENT_LINKS)


class ContentGovernanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "content.sqlite3"
        conn = sqlite3.connect(self.database)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "learning_content.sql").read_text(encoding="utf-8"))
            apply_migrations(conn, ROOT / "database" / "migrations")
        finally:
            conn.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_all_published_links_have_stable_keys_and_governance_state(self):
        targets = CONTENT_LINKS.load_targets(self.database)
        self.assertEqual(238, len(targets))
        self.assertEqual([], CONTENT_LINKS.validate_targets(targets))
        self.assertEqual({"learning": 104, "tools": 134}, CONTENT_LINKS.summary(targets)["domains"])

    def test_http_status_classification_is_conservative(self):
        self.assertEqual("healthy", CONTENT_LINKS.classify_http_status(204))
        self.assertEqual("healthy", CONTENT_LINKS.classify_http_status(302))
        self.assertEqual("degraded", CONTENT_LINKS.classify_http_status(403))
        self.assertEqual("degraded", CONTENT_LINKS.classify_http_status(429))
        self.assertEqual("degraded", CONTENT_LINKS.classify_http_status(0))
        self.assertEqual("degraded", CONTENT_LINKS.classify_http_status(503))
        self.assertEqual("unavailable", CONTENT_LINKS.classify_http_status(404))

    def test_probe_results_update_owned_tables_atomically(self):
        targets = CONTENT_LINKS.load_targets(self.database)
        selected = [
            next(target for target in targets if target.table == "learning_materials"),
            next(target for target in targets if target.table == "learning_node_links"),
            next(target for target in targets if target.table == "ai_tools"),
        ]
        results = [CONTENT_LINKS.LinkResult(target, 200, "healthy") for target in selected]
        CONTENT_LINKS.write_results(self.database, results, "2026-07-15T12:00:00+00:00")
        conn = sqlite3.connect(self.database)
        try:
            for target in selected:
                timestamp_column = "last_verified_at" if target.table == "learning_materials" else "last_checked_at"
                row = conn.execute(
                    f'SELECT link_status, "{timestamp_column}" FROM "{target.table}" WHERE "{target.key_column}" = ?',
                    (target.key,),
                ).fetchone()
                self.assertEqual(("healthy", "2026-07-15T12:00:00+00:00"), row)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
