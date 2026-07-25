import importlib.util
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.db.database import apply_migrations, dict_factory
from app.tools.repository import SQLiteToolCatalogRepository
from app.tools import service as tool_catalog


ROOT = Path(__file__).resolve().parents[1]


class ToolsServicesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "tools.sqlite3"
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            apply_migrations(conn, ROOT / "database" / "migrations")
        finally:
            conn.close()

        def connection_factory():
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = dict_factory
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        self.repository = SQLiteToolCatalogRepository(connection_factory)
        tool_catalog.clear_tool_catalog_cache()

    def tearDown(self):
        tool_catalog.clear_tool_catalog_cache()
        self.temp.cleanup()

    def value(self, query: str):
        conn = sqlite3.connect(self.database_path)
        try:
            return conn.execute(query).fetchone()[0]
        finally:
            conn.close()

    def test_migration_imports_complete_normalized_catalog(self):
        expected_migrations = {
            migration.name
            for migration in (ROOT / "database" / "migrations").glob("*.sql")
        }
        conn = sqlite3.connect(self.database_path)
        try:
            applied_migrations = {
                row[0]
                for row in conn.execute("SELECT version FROM schema_migrations")
            }
        finally:
            conn.close()
        self.assertEqual(expected_migrations, applied_migrations)
        self.assertEqual(136, self.value("SELECT COUNT(*) FROM ai_tools WHERE is_active = 1"))
        self.assertEqual(134, self.value("SELECT COUNT(*) FROM ai_tools WHERE is_active = 1 AND publication_status = 'published'"))
        self.assertEqual(138, self.value("SELECT COUNT(*) FROM tool_placements"))
        self.assertEqual(7, self.value("SELECT COUNT(*) FROM tool_categories WHERE is_active = 1"))
        self.assertEqual(12, self.value("SELECT COUNT(*) FROM tool_latest_slots WHERE is_active = 1"))
        self.assertEqual(0, self.value("SELECT COUNT(*) FROM pragma_foreign_key_check"))
        self.assertEqual(0, self.value("""
            SELECT COUNT(*)
            FROM tool_subcategories subcategory
            JOIN tool_categories category ON category.code = subcategory.category_code
            WHERE subcategory.is_active = 1 AND category.is_active = 0
        """))

    def test_repository_preserves_tool_facts_and_multi_category_placements(self):
        catalog = self.repository.load_catalog()
        self.assertEqual((7, 134, 136, 12), (
            len(catalog["categories"]),
            len(catalog["tools"]),
            len(catalog["placements"]),
            len(catalog["latestTools"]),
        ))
        tools = {item["id"]: item for item in catalog["tools"]}
        self.assertEqual("ChatGPT", tools["chatgpt"]["name"])
        self.assertTrue(tools["chatgpt"]["icon"].startswith("assets/icons/tools/"))
        self.assertIsInstance(tools["chatgpt"]["isFree"], bool)
        self.assertEqual("published", tools["chatgpt"]["publicationStatus"])
        self.assertEqual("unchecked", tools["chatgpt"]["linkStatus"])
        placed = [item for item in catalog["placements"] if item["toolId"] == "chatgpt"]
        self.assertGreaterEqual(len(placed), 1)

    def test_search_catalog_and_agent_context_use_database_snapshot(self):
        with patch("app.tools.service.SQLiteToolCatalogRepository", return_value=self.repository):
            tool_catalog.clear_tool_catalog_cache()
            exact = tool_catalog.search_tools("ChatGPT", limit=3)
            enterprise = tool_catalog.search_tools("企业级", limit=7)
            snapshot = tool_catalog.catalog_snapshot()
        self.assertEqual("ChatGPT", exact[0]["tool"]["name"])
        self.assertTrue(any(item["tool"]["name"] in {"Tabnine", "Glean", "Sentry", "Snyk AI"} for item in enterprise))
        self.assertEqual("tools.database", snapshot["meta"]["source"])
        self.assertEqual(134, len(snapshot["tools"]))

    def test_generated_migration_is_deterministic_and_baseline_is_frozen(self):
        script_path = ROOT / "scripts" / "generate-tool-catalog-migration.py"
        spec = importlib.util.spec_from_file_location("tool_migration_generator", script_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        generated = module.build_migration()
        self.assertEqual(generated, module.build_migration())
        latest_refresh = max((ROOT / "database" / "migrations").glob("*_tool_catalog_refresh.sql"))
        self.assertEqual(generated, latest_refresh.read_text(encoding="utf-8"))
        baseline = (ROOT / "database" / "migrations" / "010_tool_catalog_source_of_truth.sql").read_bytes()
        self.assertEqual(
            "1a489ab1f7e9c45be9e27c9a421f5fa377a41a67b627b843a9c07752b0db083f",
            hashlib.sha256(baseline).hexdigest(),
        )

    def test_free_filter_uses_shared_catalog_flag(self):
        with patch("app.tools.service.SQLiteToolCatalogRepository", return_value=self.repository):
            tool_catalog.clear_tool_catalog_cache()
            result = tool_catalog.list_tools(free_only=True, page_size=200)
        self.assertGreater(result["total"], 0)
        self.assertTrue(all(item["isFree"] for item in result["items"]))

    def test_runtime_consumers_do_not_import_frontend_tool_snapshot(self):
        backend = (ROOT / "backend" / "app" / "tools" / "service.py").read_text(encoding="utf-8")
        page = (ROOT / "frontend" / "tools.html").read_text(encoding="utf-8")
        search = (ROOT / "frontend" / "assets" / "js" / "site-search.js").read_text(encoding="utf-8")
        runtime = (ROOT / "frontend" / "assets" / "js" / "tools-page.js").read_text(encoding="utf-8")
        entry = (ROOT / "frontend" / "assets" / "js" / "tools-entry.js").read_text(encoding="utf-8")
        self.assertNotIn("tool-data.js", backend)
        self.assertNotIn('src="assets/js/tool-data.js"', page)
        self.assertNotIn('import "./tool-data.js"', search)
        self.assertIn('apiGet("/tools/catalog")', search)
        self.assertIn("querySelectorAll('[data-hot=\"free\"]')", runtime)
        self.assertIn("new URLSearchParams(window.location.search).get('q')", runtime)
        self.assertIn("initToolsPage", entry)
        self.assertNotIn("tool-data.js", entry)


if __name__ == "__main__":
    unittest.main()
