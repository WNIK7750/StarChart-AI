import sqlite3
import hashlib
from functools import lru_cache
from typing import Any

from app.learning import LearningService, get_learning_service
from app.users.learning_state.ports import UserLearningStateRepository
from app.users.learning_state.repositories.sqlite import SQLiteUserLearningStateRepository


class LearningStateNotFoundError(LookupError):
    def __init__(self, message: str, code: str = "LEARNING_TARGET_NOT_FOUND"):
        super().__init__(message)
        self.code = code


class LearningStateConflictError(RuntimeError):
    def __init__(self, message: str, code: str = "PROGRESS_CONFLICT"):
        super().__init__(message)
        self.code = code


class LearningStateValidationError(ValueError):
    def __init__(self, message: str, code: str = "INVALID_LEARNING_STATE"):
        super().__init__(message)
        self.code = code


class UserLearningStateService:
    def __init__(self, repository: UserLearningStateRepository, learning: LearningService):
        self.repository = repository
        self.learning = learning

    def _node(self, slug: str) -> dict[str, Any]:
        item = self.learning.resolve_reference("learning_node", slug)
        if not item:
            raise LearningStateNotFoundError("Learning node not found", "LEARNING_NODE_NOT_FOUND")
        return item

    def _enrich(self, item: dict[str, Any]) -> dict[str, Any]:
        reference = self.learning.resolve_reference(item["targetType"], item["targetKey"])
        return {
            **item,
            "title": (reference or {}).get("title") or item.get("titleSnapshot") or "内容已下线",
            "description": (reference or {}).get("description") or item.get("descriptionSnapshot"),
            "href": (reference or {}).get("href"),
            "isAvailable": bool(reference),
        }

    def list_progress(self, user_id: int) -> dict[str, Any]:
        items = []
        for progress in self.repository.list_progress(user_id):
            node = self._node(progress["nodeSlug"])
            items.append({**progress, "title": node["title"], "description": node["description"], "href": node["href"]})
        return {"items": items, "meta": {"source": "users.learning_state", "contractVersion": 1}}

    def set_progress(self, user_id: int, node_slug: str, percent: int, status: str | None = None, expected_version: int | None = None) -> dict[str, Any]:
        node = self._node(node_slug)
        resolved_status = status or ("completed" if percent == 100 else "not_started" if percent == 0 else "in_progress")
        valid_ranges = {
            "not_started": percent == 0,
            "in_progress": 1 <= percent <= 99,
            "completed": percent == 100,
            "skipped": percent == 0,
        }
        if not valid_ranges.get(resolved_status, False):
            raise LearningStateValidationError(
                f"Progress {percent}% is incompatible with status {resolved_status}",
                "INVALID_PROGRESS_STATE",
            )
        try:
            outline = self.learning.get_node(node_slug)["outline"]
            sync_sections = resolved_status == "completed" or (resolved_status == "in_progress" and percent <= 5)
            item = self.repository.upsert_progress(
                user_id,
                node_slug,
                resolved_status,
                percent,
                expected_version,
                [section["sectionUid"] for section in outline] if sync_sections else None,
                resolved_status == "completed" if sync_sections else None,
            )
        except sqlite3.IntegrityError as exc:
            if "PROGRESS_VERSION_CONFLICT" in str(exc):
                raise LearningStateConflictError("Progress was updated on another client") from exc
            raise
        return {"progress": {**item, "title": node["title"], "href": node["href"]}}

    def node_state(self, user_id: int, node_slug: str) -> dict[str, Any]:
        node = self._node(node_slug)
        outline = self.learning.get_node(node_slug)["outline"]
        stored = {item["sectionUid"]: item for item in self.repository.list_section_progress(user_id, node_slug)}
        sections = []
        for section in outline:
            state = stored.get(section["sectionUid"], {})
            sections.append({
                "sectionUid": section["sectionUid"], "nodeSlug": node_slug,
                "isCompleted": bool(state.get("isCompleted", False)),
                "completedAt": state.get("completedAt"), "version": state.get("version", 0),
                "updatedAt": state.get("updatedAt"), "chapterNo": section["chapterNo"],
                "sectionNo": section["sectionNo"], "title": section["title"],
            })
        progress = self.repository.get_progress(user_id, node_slug)
        enriched_progress = {**progress, "title": node["title"], "description": node["description"], "href": node["href"]} if progress else None
        completed = sum(1 for section in sections if section["isCompleted"])
        return {
            "nodeSlug": node_slug, "progress": enriched_progress, "sections": sections,
            "summary": {"completedCount": completed, "totalCount": len(sections), "progressPercent": progress["progressPercent"] if progress else 0},
            "meta": {"source": "users.learning_state", "contractVersion": 1},
        }

    def set_section_progress(
        self,
        user_id: int,
        node_slug: str,
        section_uid: str,
        is_completed: bool,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        node = self._node(node_slug)
        outline = self.learning.get_node(node_slug)["outline"]
        section = next((item for item in outline if item["sectionUid"] == section_uid), None)
        if not section:
            reference = self.learning.resolve_reference("learning_section", section_uid)
            code = "SECTION_NODE_MISMATCH" if reference else "LEARNING_SECTION_NOT_FOUND"
            raise LearningStateNotFoundError("Learning section does not belong to this node", code)
        try:
            result = self.repository.set_section_progress(
                user_id, node_slug, section_uid, is_completed, expected_version, len(outline)
            )
        except sqlite3.IntegrityError as exc:
            if "SECTION_PROGRESS_VERSION_CONFLICT" in str(exc):
                raise LearningStateConflictError(
                    "Section progress was updated on another client", "SECTION_PROGRESS_CONFLICT"
                ) from exc
            raise
        completed = result.pop("completedCount")
        progress = {**result["progress"], "title": node["title"], "description": node["description"], "href": node["href"]}
        section_state = {
            **result["section"], "isCompleted": bool(result["section"]["isCompleted"]),
            "chapterNo": section["chapterNo"], "sectionNo": section["sectionNo"], "title": section["title"],
        }
        return {
            "section": section_state, "progress": progress,
            "summary": {"completedCount": completed, "totalCount": len(outline), "progressPercent": progress["progressPercent"]},
        }

    def record_activity(self, user_id: int, item: dict[str, Any]) -> dict[str, Any]:
        reference = self.learning.resolve_reference(item["targetType"], item["targetKey"])
        if not reference:
            raise LearningStateNotFoundError("Learning target not found")
        expected_targets = {
            "view_node": "learning_node",
            "start_material": "learning_material",
            "open_resource": "learning_link",
            "complete_section": "learning_material",
        }
        if expected_targets.get(item["activityType"]) != item["targetType"]:
            raise LearningStateValidationError(
                "Activity type is incompatible with target type",
                "INVALID_ACTIVITY_TARGET",
            )
        if item.get("nodeSlug"):
            self._node(item["nodeSlug"])
            reference_node = reference.get("nodeSlug") or (reference["targetKey"] if item["targetType"] == "learning_node" else None)
            if reference_node and reference_node != item["nodeSlug"]:
                raise LearningStateValidationError(
                    "Learning target does not belong to the supplied node",
                    "LEARNING_TARGET_NODE_MISMATCH",
                )
        if item["activityType"] == "complete_section" and not item.get("metadata", {}).get("sectionId"):
            raise LearningStateValidationError(
                "complete_section requires metadata.sectionId",
                "SECTION_ID_REQUIRED",
            )
        activity = self.repository.record_activity(user_id, item)
        return {"activity": self._enrich(activity)}

    def import_anonymous_state(self, user_id: int, snapshot_id: str, node_views: list[dict[str, Any]]) -> dict[str, Any]:
        latest_by_slug = {}
        for item in node_views:
            current = latest_by_slug.get(item["nodeSlug"])
            if not current or item["viewedAt"] > current["viewedAt"]:
                latest_by_slug[item["nodeSlug"]] = item
        validated = sorted(latest_by_slug.values(), key=lambda value: value["viewedAt"])
        for item in validated:
            self._node(item["nodeSlug"])

        imported = 0
        replayed = 0
        for item in validated:
            digest = hashlib.sha256(f"{snapshot_id}:{item['nodeSlug']}".encode("utf-8")).hexdigest()[:48]
            result = self.record_activity(user_id, {
                "nodeSlug": item["nodeSlug"],
                "targetType": "learning_node",
                "targetKey": item["nodeSlug"],
                "activityType": "view_node",
                "metadata": {"source": "anonymous_import", "viewedAt": item["viewedAt"].isoformat()},
                "idempotencyKey": f"anon_{digest}",
            })
            if result["activity"]["idempotencyReplayed"]:
                replayed += 1
            else:
                imported += 1
        return {
            "importedActivityCount": imported,
            "replayedActivityCount": replayed,
            "meta": {"source": "users.learning_state", "contractVersion": 1},
        }

    def recent(self, user_id: int, page: int = 1, page_size: int = 10) -> dict[str, Any]:
        items = [self._enrich(item) for item in self.repository.recent(user_id, page_size, (page - 1) * page_size)]
        total = self.repository.recent_count(user_id)
        return {"items": items, "meta": {"page": page, "pageSize": page_size, "totalCount": total, "hasNext": page * page_size < total, "source": "users.learning_state", "contractVersion": 1}}

    def resume(self, user_id: int) -> dict[str, Any]:
        progress_items = self.repository.list_progress(user_id)
        current = next((item for item in progress_items if item["status"] == "in_progress"), None)
        if current:
            node = self._node(current["nodeSlug"])
            return {"item": {**current, "title": node["title"], "description": node["description"], "href": node["href"], "reasonCode": "RESUME_IN_PROGRESS"}}
        recent_nodes = [item for item in self.repository.recent(user_id, 20, 0) if item.get("nodeSlug")]
        if recent_nodes:
            node = self._node(recent_nodes[0]["nodeSlug"])
            return {"item": {**recent_nodes[0], "title": node["title"], "description": node["description"], "href": node["href"], "reasonCode": "CONTINUE_RECENT"}}
        recommended = self.learning.search("", 1)["items"]
        item = {**recommended[0], "reasonCode": "START_RECOMMENDED"} if recommended else None
        return {"item": item}

    def list_favorites(self, user_id: int, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        items = [self._enrich(item) for item in self.repository.list_favorites(user_id, page_size, (page - 1) * page_size)]
        total = self.repository.favorites_count(user_id)
        return {"items": items, "meta": {"page": page, "pageSize": page_size, "totalCount": total, "hasNext": page * page_size < total, "source": "users.learning_state", "contractVersion": 1}}

    def add_favorite(self, user_id: int, target_type: str, target_key: str) -> dict[str, Any]:
        reference = self.learning.resolve_reference(target_type, target_key)
        if not reference:
            raise LearningStateNotFoundError("Favorite target not found", "FAVORITE_TARGET_NOT_FOUND")
        item = self.repository.add_favorite(user_id, {"targetType": target_type, "targetKey": target_key, "title": reference["title"], "description": reference.get("description")})
        return {"favorite": self._enrich(item)}

    def remove_favorite(self, user_id: int, favorite_uid: str) -> None:
        if not self.repository.remove_favorite(user_id, favorite_uid):
            raise LearningStateNotFoundError("Favorite not found", "FAVORITE_NOT_FOUND")

    def dashboard(self, user_id: int) -> dict[str, Any]:
        progress = self.list_progress(user_id)["items"]
        return {
            "resume": self.resume(user_id)["item"],
            "recent": self.recent(user_id, 1, 5)["items"],
            "favorites": self.list_favorites(user_id, 1, 5)["items"],
            "summary": {
                "startedCount": sum(1 for item in progress if item["status"] == "in_progress"),
                "completedCount": sum(1 for item in progress if item["status"] == "completed"),
                "overallPercent": round(sum(item["progressPercent"] for item in progress) / len(progress)) if progress else 0,
            },
            "meta": {"source": "users.learning_state", "contractVersion": 1},
        }


@lru_cache(maxsize=1)
def get_user_learning_state_service() -> UserLearningStateService:
    return UserLearningStateService(SQLiteUserLearningStateRepository(), get_learning_service())
