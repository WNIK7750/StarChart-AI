import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from app.db.database import apply_migrations, dict_factory
from app.learning.repositories.sqlite import SQLiteLearningRepository
from app.learning.schemas import LearningNodeResponse, NodeRelationsResponse, RoadmapResponse
from app.learning.service import LearningNotFoundError, LearningService
from app.users.learning_state.repositories.sqlite import SQLiteUserLearningStateRepository
from app.users.learning_state.schemas import DashboardResponse, NodeLearningStateResponse, ProgressListResponse, RecentResponse, SectionProgressResponse
from app.users.learning_state.service import LearningStateConflictError, LearningStateNotFoundError, LearningStateValidationError, UserLearningStateService


ROOT = Path(__file__).resolve().parents[1]


class LearningServicesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp.name) / "test.sqlite3"
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "learning_content.sql").read_text(encoding="utf-8"))
            apply_migrations(conn, ROOT / "database" / "migrations")
            for uid, username in (("usr_test_1", "test_one"), ("usr_test_2", "test_two")):
                conn.execute("INSERT INTO user_accounts(user_uid, username) VALUES (?, ?)", (uid, username))
            self.user_ids = [row[0] for row in conn.execute("SELECT id FROM user_accounts ORDER BY id DESC LIMIT 2").fetchall()][::-1]
            conn.commit()
        finally:
            conn.close()

        def connection_factory():
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = dict_factory
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

        self.learning = LearningService(SQLiteLearningRepository(connection_factory))
        self.users = UserLearningStateService(SQLiteUserLearningStateRepository(connection_factory), self.learning)

    def tearDown(self):
        self.temp.cleanup()

    def database_value(self, query, params=()):
        conn = sqlite3.connect(self.database_path)
        try:
            return conn.execute(query, params).fetchone()[0]
        finally:
            conn.close()

    def test_learning_service_preserves_core_contract(self):
        roadmap = self.learning.get_roadmap()
        node = self.learning.get_node("ai-literacy")
        self.assertEqual(16, len(roadmap["nodes"]))
        self.assertEqual("0 0 1320 430", roadmap["viewBox"])
        self.assertEqual(180, node["stats"]["suggestedMinutes"])
        self.assertEqual("3h", node["stats"]["suggestedDuration"])
        self.assertEqual("rag", self.learning.search("RAG", 1)["items"][0]["slug"])
        RoadmapResponse.model_validate(roadmap)
        LearningNodeResponse.model_validate(node)
        with self.assertRaises(ValidationError):
            RoadmapResponse.model_validate({**roadmap, "unexpected": True})

    def test_learning_contract_snapshot_and_semantic_relations(self):
        snapshot = json.loads((ROOT / "tests" / "contracts" / "learning_contract_v1.json").read_text(encoding="utf-8"))
        roadmap = self.learning.get_roadmap()
        node = self.learning.get_node("prompt")
        relations = self.learning.get_relations("prompt")
        self.assertEqual(snapshot["roadmap"], list(roadmap))
        self.assertEqual(snapshot["roadmapEdge"], list(roadmap["edges"][0]))
        self.assertEqual(snapshot["node"], list(node))
        self.assertEqual(snapshot["section"], list(node["outline"][0]))
        self.assertEqual(snapshot["relations"], list(relations["relations"]))
        self.assertTrue(node["outline"][0]["sectionUid"].startswith("sec_"))
        self.assertTrue(relations["relations"]["prerequisites"])
        NodeRelationsResponse.model_validate(relations)

    def test_content_governance_uses_stable_ids_and_publication_filter(self):
        node = self.learning.get_node("prompt")
        material = node["mainMaterial"]
        resource = node["resources"][0]
        self.assertTrue(material["materialUid"].startswith("mat_"))
        self.assertEqual("published", material["publicationStatus"])
        self.assertEqual("unchecked", material["linkStatus"])
        self.assertEqual(1, material["contentVersion"])
        self.assertTrue(resource["linkUid"].startswith("lnk_"))
        self.assertEqual("unchecked", resource["linkStatus"])
        legacy = self.learning.resolve_reference("learning_material", str(material["materialId"]))
        stable = self.learning.resolve_reference("learning_material", material["materialUid"])
        self.assertEqual(material["materialUid"], legacy["targetKey"])
        self.assertEqual(legacy, stable)
        conn = sqlite3.connect(self.database_path)
        try:
            conn.execute("UPDATE learning_materials SET publication_status = 'archived' WHERE material_uid = ?", (material["materialUid"],))
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(LearningNotFoundError):
            self.learning.get_node("prompt")

    def test_recent_reading_does_not_invent_progress(self):
        user_id = self.user_ids[0]
        created = self.users.record_activity(user_id, {
            "nodeSlug": "rag",
            "targetType": "learning_node",
            "targetKey": "rag",
            "activityType": "view_node",
            "metadata": {},
            "idempotencyKey": "view-rag-1",
        })
        replayed = self.users.record_activity(user_id, {
            "nodeSlug": "rag",
            "targetType": "learning_node",
            "targetKey": "rag",
            "activityType": "view_node",
            "metadata": {},
            "idempotencyKey": "view-rag-1",
        })
        self.assertFalse(created["activity"]["idempotencyReplayed"])
        self.assertTrue(replayed["activity"]["idempotencyReplayed"])
        recent = self.users.recent(user_id)["items"]
        self.assertEqual("rag", recent[0]["targetKey"])
        self.assertEqual([], self.users.list_progress(user_id)["items"])
        self.assertEqual("CONTINUE_RECENT", self.users.resume(user_id)["item"]["reasonCode"])
        self.assertEqual(1, self.database_value("SELECT COUNT(*) FROM user_learning_activity WHERE user_id = ?", (user_id,)))

    def test_anonymous_reading_import_is_validated_idempotent_and_progress_free(self):
        user_id = self.user_ids[0]
        viewed_at = datetime(2026, 7, 12, 8, 0, tzinfo=timezone.utc)
        payload = [
            {"nodeSlug": "rag", "viewedAt": viewed_at},
            {"nodeSlug": "prompt", "viewedAt": viewed_at},
            {"nodeSlug": "rag", "viewedAt": viewed_at},
        ]
        first = self.users.import_anonymous_state(user_id, "snapshot_test_001", payload)
        second = self.users.import_anonymous_state(user_id, "snapshot_test_001", payload)
        self.assertEqual(2, first["importedActivityCount"])
        self.assertEqual(0, first["replayedActivityCount"])
        self.assertEqual(0, second["importedActivityCount"])
        self.assertEqual(2, second["replayedActivityCount"])
        self.assertEqual([], self.users.list_progress(user_id)["items"])
        self.assertEqual(2, self.database_value("SELECT COUNT(*) FROM user_learning_activity WHERE user_id = ?", (user_id,)))
        with self.assertRaises(LearningStateNotFoundError):
            self.users.import_anonymous_state(user_id, "snapshot_test_002", [
                {"nodeSlug": "ai-literacy", "viewedAt": viewed_at},
                {"nodeSlug": "missing-node", "viewedAt": viewed_at},
            ])
        self.assertEqual(2, self.database_value("SELECT COUNT(*) FROM user_learning_activity WHERE user_id = ?", (user_id,)))

    def test_progress_is_user_owned_and_isolated(self):
        first, second = self.user_ids
        result = self.users.set_progress(first, "rag", 40)
        self.assertEqual("in_progress", result["progress"]["status"])
        self.assertEqual(40, self.users.list_progress(first)["items"][0]["progressPercent"])
        self.assertEqual([], self.users.list_progress(second)["items"])
        self.assertEqual("RESUME_IN_PROGRESS", self.users.resume(first)["item"]["reasonCode"])
        updated = self.users.set_progress(first, "rag", 60, expected_version=result["progress"]["version"])
        self.assertEqual(2, updated["progress"]["version"])
        with self.assertRaises(LearningStateConflictError):
            self.users.set_progress(first, "rag", 80, expected_version=result["progress"]["version"])
        self.assertEqual(2, self.database_value("SELECT COUNT(*) FROM user_audit_logs WHERE actor_user_id = ? AND action = 'learning.progress.updated'", (first,)))
        with self.assertRaises(LearningStateValidationError):
            self.users.set_progress(first, "rag", 100, status="in_progress")

    def test_section_progress_is_atomic_versioned_and_user_owned(self):
        first, second = self.user_ids
        initial = self.users.node_state(first, "ai-literacy")
        section = initial["sections"][0]
        self.assertEqual(0, section["version"])
        updated = self.users.set_section_progress(first, "ai-literacy", section["sectionUid"], True, 0)
        self.assertTrue(updated["section"]["isCompleted"])
        self.assertEqual(1, updated["section"]["version"])
        self.assertEqual(1, updated["summary"]["completedCount"])
        self.assertEqual([], [item for item in self.users.node_state(second, "ai-literacy")["sections"] if item["isCompleted"]])
        with self.assertRaises(LearningStateConflictError) as conflict:
            self.users.set_section_progress(first, "ai-literacy", section["sectionUid"], False, 0)
        self.assertEqual("SECTION_PROGRESS_CONFLICT", conflict.exception.code)
        self.assertEqual(1, self.database_value(
            "SELECT COUNT(*) FROM user_audit_logs WHERE actor_user_id = ? AND action = 'learning.section_progress.updated'",
            (first,),
        ))
        NodeLearningStateResponse.model_validate(self.users.node_state(first, "ai-literacy"))
        SectionProgressResponse.model_validate(updated)

    def test_manual_node_completion_keeps_section_state_consistent(self):
        user_id = self.user_ids[0]
        complete = self.users.set_progress(user_id, "prompt", 100, "completed")
        state = self.users.node_state(user_id, "prompt")
        self.assertEqual(100, complete["progress"]["progressPercent"])
        self.assertTrue(all(section["isCompleted"] for section in state["sections"]))
        self.users.set_progress(user_id, "prompt", 5, "in_progress", complete["progress"]["version"])
        reset = self.users.node_state(user_id, "prompt")
        self.assertFalse(any(section["isCompleted"] for section in reset["sections"]))
        with self.assertRaises(LearningStateNotFoundError) as mismatch:
            self.users.set_section_progress(user_id, "rag", state["sections"][0]["sectionUid"], True, 0)
        self.assertEqual("SECTION_NODE_MISMATCH", mismatch.exception.code)

    def test_activity_target_invariants(self):
        user_id = self.user_ids[0]
        with self.assertRaises(LearningStateValidationError):
            self.users.record_activity(user_id, {
                "nodeSlug": "rag",
                "targetType": "learning_node",
                "targetKey": "rag",
                "activityType": "start_material",
                "metadata": {},
                "idempotencyKey": "invalid-target-1",
            })
        rag = self.learning.get_node("rag")
        with self.assertRaises(LearningStateValidationError):
            self.users.record_activity(user_id, {
                "nodeSlug": "prompt",
                "targetType": "learning_material",
                "targetKey": str(rag["mainMaterial"]["materialId"]),
                "activityType": "start_material",
                "metadata": {},
                "idempotencyKey": "invalid-node-1",
            })
        self.assertEqual(0, self.database_value("SELECT COUNT(*) FROM user_learning_activity WHERE user_id = ?", (user_id,)))

    def test_favorite_is_idempotent_and_removable(self):
        user_id = self.user_ids[0]
        first = self.users.add_favorite(user_id, "learning_node", "rag")["favorite"]
        second = self.users.add_favorite(user_id, "learning_node", "rag")["favorite"]
        self.assertEqual(first["favoriteUid"], second["favoriteUid"])
        self.assertEqual(1, len(self.users.list_favorites(user_id)["items"]))
        self.users.remove_favorite(user_id, first["favoriteUid"])
        self.assertEqual([], self.users.list_favorites(user_id)["items"])
        self.assertEqual(2, self.database_value("SELECT COUNT(*) FROM user_audit_logs WHERE actor_user_id = ? AND resource_type = 'favorite'", (user_id,)))

    def test_pagination_and_user_state_contracts(self):
        user_id = self.user_ids[0]
        for slug in ("rag", "prompt"):
            self.users.record_activity(user_id, {
                "nodeSlug": slug,
                "targetType": "learning_node",
                "targetKey": slug,
                "activityType": "view_node",
                "metadata": {},
                "idempotencyKey": f"view-{slug}-page",
            })
        first_page = self.users.recent(user_id, page=1, page_size=1)
        second_page = self.users.recent(user_id, page=2, page_size=1)
        self.assertEqual(2, first_page["meta"]["totalCount"])
        self.assertTrue(first_page["meta"]["hasNext"])
        self.assertFalse(second_page["meta"]["hasNext"])
        RecentResponse.model_validate(first_page)
        ProgressListResponse.model_validate(self.users.list_progress(user_id))
        DashboardResponse.model_validate(self.users.dashboard(user_id))


class MigrationTest(unittest.TestCase):
    def test_migration_checksum_detects_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            migration = root / "001_example.sql"
            migration.write_text("CREATE TABLE example (id INTEGER PRIMARY KEY);", encoding="utf-8")
            database = root / "migration.sqlite3"
            conn = sqlite3.connect(database)
            try:
                apply_migrations(conn, root)
                self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0])
                apply_migrations(conn, root)
                migration.write_text("CREATE TABLE example (id INTEGER PRIMARY KEY, name TEXT);", encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    apply_migrations(conn, root)
            finally:
                conn.close()

    def test_conditional_column_migration_supports_legacy_and_current_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "001_compat.sql").write_text(
                "-- ai-nav:add-column-if-missing user_accounts token_version INTEGER NOT NULL DEFAULT 0\n"
                "CREATE TABLE IF NOT EXISTS user_security_questions (id INTEGER PRIMARY KEY);\n",
                encoding="utf-8",
            )
            for include_column in (False, True):
                conn = sqlite3.connect(":memory:")
                try:
                    suffix = ", token_version INTEGER NOT NULL DEFAULT 0" if include_column else ""
                    conn.execute(f"CREATE TABLE user_accounts (id INTEGER PRIMARY KEY{suffix})")
                    apply_migrations(conn, root)
                    columns = {row[1] for row in conn.execute("PRAGMA table_info(user_accounts)")}
                    self.assertIn("token_version", columns)
                    self.assertIsNotNone(
                        conn.execute(
                            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'user_security_questions'"
                        ).fetchone()
                    )
                    apply_migrations(conn, root)
                finally:
                    conn.close()

    def test_failed_conditional_migration_rolls_back_column_and_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "001_broken.sql").write_text(
                "-- ai-nav:add-column-if-missing user_accounts token_version INTEGER DEFAULT 0\n"
                "CREATE TABLE valid_table (id INTEGER PRIMARY KEY);\n"
                "THIS IS NOT SQL;\n",
                encoding="utf-8",
            )
            conn = sqlite3.connect(":memory:")
            try:
                conn.execute("CREATE TABLE user_accounts (id INTEGER PRIMARY KEY)")
                with self.assertRaises(sqlite3.Error):
                    apply_migrations(conn, root)
                columns = {row[1] for row in conn.execute("PRAGMA table_info(user_accounts)")}
                self.assertNotIn("token_version", columns)
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0])
            finally:
                conn.close()

    def test_conditional_column_directive_rejects_forbidden_syntax(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "001_unsafe.sql").write_text(
                "-- ai-nav:add-column-if-missing user_accounts token_version INTEGER DEFAULT 0; DROP TABLE user_accounts\n",
                encoding="utf-8",
            )
            conn = sqlite3.connect(":memory:")
            try:
                conn.execute("CREATE TABLE user_accounts (id INTEGER PRIMARY KEY)")
                with self.assertRaisesRegex(RuntimeError, "forbidden syntax"):
                    apply_migrations(conn, root)
                self.assertIsNotNone(
                    conn.execute("SELECT name FROM sqlite_master WHERE name = 'user_accounts'").fetchone()
                )
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
