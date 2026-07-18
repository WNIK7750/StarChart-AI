from functools import lru_cache
from typing import Any

from app.learning.policies import format_duration, site_learning_node_href
from app.learning.ports import LearningRepository
from app.learning.repositories.sqlite import SQLiteLearningRepository


class LearningNotFoundError(LookupError):
    def __init__(self, message: str, code: str = "LEARNING_NOT_FOUND"):
        super().__init__(message)
        self.code = code


class LearningService:
    def __init__(self, repository: LearningRepository):
        self.repository = repository

    def get_roadmap(self) -> dict[str, Any]:
        data = self.repository.roadmap()
        grouped: dict[str, list[str]] = {}
        for item in data["relations"]:
            grouped.setdefault(item["domainCode"], []).append(item["nodeSlug"])
        return {"domains": data["domains"], "difficultyLevels": data["levels"], "nodes": data["nodes"], "edges": data["edges"], "domainNodes": grouped, "viewBox": "0 0 1320 430", "meta": {"contractVersion": 1}}

    def list_resources(self, domain: str | None = None) -> dict[str, Any]:
        return {"items": self.repository.resources(domain), "meta": {"contractVersion": 1}}

    def get_node(self, slug: str) -> dict[str, Any]:
        bundle = self.repository.node_bundle(slug)
        if not bundle:
            raise LearningNotFoundError("Learning node not found", "LEARNING_NODE_NOT_FOUND")
        if not bundle.get("material"):
            raise LearningNotFoundError("Learning material not found", "LEARNING_MATERIAL_NOT_FOUND")
        node = dict(bundle["node"])
        material = dict(bundle["material"])
        outline = bundle["outline"]
        suggested_minutes = sum(item["durationMinutes"] for item in outline)
        material_id = material.pop("id")
        node.pop("sortOrder", None)
        relations = self.get_relations(slug)["relations"]
        return {
            "node": node,
            "mainMaterial": {**material, "materialId": material_id},
            "overview": {"title": f"为什么学习「{node['title']}」", "body": material["overview"]},
            "outline": outline,
            "resources": bundle["resources"],
            "tags": [item["tag"] for item in bundle["tags"]],
            "stats": {"chapterCount": len({item["chapterNo"] for item in outline}), "sectionCount": len(outline), "suggestedMinutes": suggested_minutes, "suggestedDuration": format_duration(suggested_minutes)},
            "navigation": {"previous": bundle["previous"], "next": bundle["next"]},
            "relations": relations,
            "meta": {"contractVersion": 1, "sourceMaterialId": material_id, "durationRule": "suggestedMinutes is the sum of active learning_material_sections.duration_minutes for the primary material."},
        }

    def get_relations(self, slug: str) -> dict[str, Any]:
        if not self.repository.resolve_reference("learning_node", slug):
            raise LearningNotFoundError("Learning node not found", "LEARNING_NODE_NOT_FOUND")
        relations = {
            key: [{**item, "href": site_learning_node_href(item["slug"])} for item in items]
            for key, items in self.repository.node_relations(slug).items()
        }
        return {"nodeSlug": slug, "relations": relations, "meta": {"contractVersion": 1}}

    def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        items = [{**item, "href": site_learning_node_href(item["slug"])} for item in self.repository.search(query, limit)]
        return {"query": query, "items": items, "meta": {"contractVersion": 1}}

    def get_agent_context(self, query: str, limit: int = 7) -> dict[str, Any]:
        result = self.search(query, limit)
        nodes = []
        for item in result["items"]:
            relations = self.repository.node_relations(item["slug"])
            nodes.append({
                "slug": item["slug"], "title": item["title"], "summary": item["summary"],
                "difficultyCode": item["difficultyCode"], "href": item["href"],
                "prerequisiteSlugs": [relation["slug"] for relation in relations["prerequisites"]],
                "recommendedNextSlugs": [relation["slug"] for relation in relations["recommendedNext"]],
                "evidence": {"sourceType": "learning_node", "sourceKey": item["slug"]},
            })
        return {"query": query, "nodes": nodes, "meta": {"contractVersion": 1}}

    def recommend_next(self, slug: str) -> dict[str, Any] | None:
        item = self.repository.next_node(slug)
        return {**item, "href": site_learning_node_href(item["slug"])} if item else None

    def resolve_reference(self, target_type: str, target_key: str) -> dict[str, Any] | None:
        item = self.repository.resolve_reference(target_type, target_key)
        if not item:
            return None
        node_slug = item["targetKey"] if target_type == "learning_node" else item.get("nodeSlug")
        href = site_learning_node_href(node_slug) if node_slug else None
        return {**item, "targetType": target_type, "href": href}


@lru_cache(maxsize=1)
def get_learning_service() -> LearningService:
    return LearningService(SQLiteLearningRepository())
