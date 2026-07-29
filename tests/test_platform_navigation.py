import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db.database import apply_migrations


ROOT = Path(__file__).resolve().parents[1]


class PlatformNavigationTest(unittest.TestCase):
    def test_navigation_points_only_to_real_product_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = sqlite3.connect(Path(directory) / "navigation.sqlite3")
            connection.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            connection.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            apply_migrations(connection, ROOT / "database" / "migrations")
            rows = dict(connection.execute("SELECT code, href FROM navigation_items WHERE is_active = 1"))
            connection.close()

        self.assertEqual("/", rows["home"])
        self.assertEqual("/learn", rows["learn"])
        self.assertEqual("/tools", rows["tools"])
        self.assertEqual("/assistant", rows["assistant"])
        self.assertNotIn("about", rows)

    def test_learning_resources_use_canonical_node_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = sqlite3.connect(Path(directory) / "navigation.sqlite3")
            connection.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            connection.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            apply_migrations(connection, ROOT / "database" / "migrations")
            hrefs = [
                row[0]
                for row in connection.execute(
                    "SELECT href FROM learning_resources ORDER BY id"
                )
            ]
            connection.close()

        self.assertTrue(hrefs)
        self.assertTrue(all(href.startswith("/learn/") for href in hrefs), hrefs)


if __name__ == "__main__":
    unittest.main()
