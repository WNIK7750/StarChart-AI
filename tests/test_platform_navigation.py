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

        self.assertEqual("assistant.html", rows["assistant"])
        self.assertNotIn("about", rows)
        for href in rows.values():
            page = href.split("?", 1)[0].split("#", 1)[0]
            self.assertTrue((ROOT / "frontend" / page).is_file(), href)


if __name__ == "__main__":
    unittest.main()
