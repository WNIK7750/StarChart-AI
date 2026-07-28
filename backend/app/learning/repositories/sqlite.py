from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Any, Iterator

from app.db.database import get_connection


class SQLiteLearningRepository:
    def __init__(self, connection_factory: Callable[[], Connection] = get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        conn = self._connection_factory()
        try:
            yield conn
        finally:
            conn.close()

    def roadmap(self) -> dict[str, Any]:
        with self._connect() as conn:
            domains = conn.execute(
                "SELECT code, name, color, glow_color AS glowColor, description FROM knowledge_domains WHERE is_active = 1 ORDER BY sort_order, id"
            ).fetchall()
            levels = conn.execute(
                "SELECT code, name, color FROM difficulty_levels WHERE is_active = 1 ORDER BY sort_order, id"
            ).fetchall()
            nodes = conn.execute(
                """
                SELECT n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode,
                       d.color, n.x, n.y, n.width, n.height, n.is_current AS isCurrent
                FROM roadmap_nodes n JOIN difficulty_levels d ON d.code = n.difficulty_code
                WHERE n.is_active = 1 ORDER BY n.sort_order, n.id
                """
            ).fetchall()
            edges = conn.execute(
                """
                SELECT from_slug AS fromSlug, to_slug AS toSlug, path_d AS pathD,
                       line_type AS lineType, relation_type AS relationType
                FROM roadmap_edges WHERE is_active = 1 ORDER BY sort_order, id
                """
            ).fetchall()
            relations = conn.execute(
                "SELECT domain_code AS domainCode, node_slug AS nodeSlug FROM roadmap_domain_nodes"
            ).fetchall()
        return {"domains": domains, "levels": levels, "nodes": nodes, "edges": edges, "relations": relations}

    def resources(self, domain: str | None = None) -> list[dict[str, Any]]:
        params: list[Any] = []
        where = "r.is_active = 1"
        if domain:
            where += " AND EXISTS (SELECT 1 FROM roadmap_domain_nodes dn WHERE dn.node_slug = r.node_slug AND dn.domain_code = ?)"
            params.append(domain)
        with self._connect() as conn:
            return conn.execute(
                f"""
                SELECT r.slug, r.title, r.description, r.cover_label AS coverLabel,
                       r.cover_text AS coverText, r.cover_theme AS coverTheme, r.href, r.node_slug AS nodeSlug
                FROM learning_resources r WHERE {where} ORDER BY r.sort_order, r.id
                """,
                params,
            ).fetchall()

    def node_bundle(self, slug: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            node = conn.execute(
                """
                SELECT n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode,
                       d.name AS difficultyName, d.color, n.sort_order AS sortOrder
                FROM roadmap_nodes n JOIN difficulty_levels d ON d.code = n.difficulty_code
                WHERE n.slug = ? AND n.is_active = 1
                """,
                (slug,),
            ).fetchone()
            if not node:
                return None
            material = conn.execute(
                """
                SELECT id, material_uid AS materialUid, title, provider,
                       material_type AS materialType, url, start_url AS startUrl,
                       language, access_type AS accessType, cover_label AS coverLabel,
                       cover_text AS coverText, cover_theme AS coverTheme, description, overview,
                       publication_status AS publicationStatus, content_version AS contentVersion,
                       quality_status AS qualityStatus, source_trust AS sourceTrust,
                       last_verified_at AS lastVerifiedAt, link_status AS linkStatus
                FROM learning_materials
                WHERE node_slug = ? AND is_primary = 1 AND is_active = 1
                  AND publication_status = 'published'
                ORDER BY sort_order, id LIMIT 1
                """,
                (slug,),
            ).fetchone()
            if not material:
                return {"node": node, "material": None}
            outline = conn.execute(
                """
                SELECT id AS sectionId, section_uid AS sectionUid,
                       chapter_no AS chapterNo, section_no AS sectionNo, title,
                       description, duration_minutes AS durationMinutes, source_url AS sourceUrl
                FROM learning_material_sections WHERE material_id = ? AND is_active = 1
                ORDER BY sort_order, chapter_no, section_no
                """,
                (material["id"],),
            ).fetchall()
            resources = conn.execute(
                """
                SELECT id AS linkId, link_uid AS linkUid, title, description, url,
                       link_type AS linkType, access_type AS accessType, accent_color AS accentColor,
                       publication_status AS publicationStatus, quality_status AS qualityStatus,
                       last_checked_at AS lastCheckedAt, link_status AS linkStatus
                FROM learning_node_links
                WHERE node_slug = ? AND is_active = 1 AND publication_status = 'published'
                ORDER BY sort_order, id
                """,
                (slug,),
            ).fetchall()
            tags = conn.execute(
                "SELECT tag FROM learning_node_tags WHERE node_slug = ? ORDER BY sort_order, tag", (slug,)
            ).fetchall()
            previous_node = conn.execute(
                "SELECT slug, title FROM roadmap_nodes WHERE is_active = 1 AND sort_order < ? ORDER BY sort_order DESC LIMIT 1",
                (node["sortOrder"],),
            ).fetchone()
            next_node = conn.execute(
                "SELECT slug, title FROM roadmap_nodes WHERE is_active = 1 AND sort_order > ? ORDER BY sort_order LIMIT 1",
                (node["sortOrder"],),
            ).fetchone()
        return {"node": node, "material": material, "outline": outline, "resources": resources, "tags": tags, "previous": previous_node, "next": next_node}

    def node_relations(self, slug: str) -> dict[str, list[dict[str, Any]]]:
        fields = "n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode, e.relation_type AS relationType"
        with self._connect() as conn:
            prerequisites = conn.execute(
                f"""
                SELECT {fields}
                FROM roadmap_edges e JOIN roadmap_nodes n ON n.slug = e.from_slug
                WHERE e.to_slug = ? AND e.relation_type = 'prerequisite'
                  AND e.is_active = 1 AND n.is_active = 1
                ORDER BY e.sort_order, e.id
                """,
                (slug,),
            ).fetchall()
            recommended = conn.execute(
                f"""
                SELECT {fields}
                FROM roadmap_edges e JOIN roadmap_nodes n ON n.slug = e.to_slug
                WHERE e.from_slug = ? AND e.relation_type IN ('prerequisite', 'recommended_next')
                  AND e.is_active = 1 AND n.is_active = 1
                ORDER BY CASE e.relation_type WHEN 'recommended_next' THEN 0 ELSE 1 END, e.sort_order, e.id
                """,
                (slug,),
            ).fetchall()
            related = conn.execute(
                f"""
                SELECT {fields}
                FROM roadmap_edges e JOIN roadmap_nodes n
                  ON n.slug = CASE WHEN e.from_slug = ? THEN e.to_slug ELSE e.from_slug END
                WHERE (e.from_slug = ? OR e.to_slug = ?) AND e.relation_type = 'related'
                  AND e.is_active = 1 AND n.is_active = 1
                ORDER BY e.sort_order, e.id
                """,
                (slug, slug, slug),
            ).fetchall()
        return {"prerequisites": prerequisites, "recommendedNext": recommended, "related": related}

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        value = query.strip()
        term = f"%{value}%"
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT DISTINCT n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode,
                       d.name AS difficultyName, COALESCE(m.description, n.subtitle) AS summary
                FROM roadmap_nodes n
                JOIN difficulty_levels d ON d.code = n.difficulty_code
                LEFT JOIN learning_materials m ON m.node_slug = n.slug AND m.is_primary = 1 AND m.is_active = 1
                LEFT JOIN learning_node_tags t ON t.node_slug = n.slug
                WHERE n.is_active = 1
                  AND (? = '' OR n.title LIKE ? OR n.subtitle LIKE ? OR m.description LIKE ? OR t.tag LIKE ?)
                ORDER BY CASE WHEN n.title = ? THEN 0 WHEN n.title LIKE ? THEN 1 ELSE 2 END, n.sort_order, n.id
                LIMIT ?
                """,
                (value, term, term, term, term, value, f"{value}%", limit),
            ).fetchall()

    def next_node(self, slug: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode
                FROM roadmap_edges e JOIN roadmap_nodes n ON n.slug = e.to_slug
                WHERE e.from_slug = ? AND e.is_active = 1 AND n.is_active = 1
                ORDER BY CASE e.relation_type WHEN 'recommended_next' THEN 0 WHEN 'prerequisite' THEN 1 ELSE 2 END,
                         e.sort_order, e.id LIMIT 1
                """,
                (slug,),
            ).fetchone()
            if row:
                return row
            return conn.execute(
                """
                SELECT n2.slug, n2.title, n2.subtitle, n2.difficulty_code AS difficultyCode
                FROM roadmap_nodes n1 JOIN roadmap_nodes n2 ON n2.sort_order > n1.sort_order
                WHERE n1.slug = ? AND n2.is_active = 1 ORDER BY n2.sort_order, n2.id LIMIT 1
                """,
                (slug,),
            ).fetchone()

    def resolve_reference(self, target_type: str, target_key: str) -> dict[str, Any] | None:
        queries = {
            "learning_node": "SELECT slug AS targetKey, title, subtitle AS description FROM roadmap_nodes WHERE slug = ? AND is_active = 1",
            "learning_material": """
                SELECT material_uid AS targetKey, node_slug AS nodeSlug, title, description
                FROM learning_materials
                WHERE (material_uid = ? OR CAST(id AS TEXT) = ?) AND is_active = 1
                  AND publication_status = 'published'
            """,
            "learning_link": """
                SELECT link_uid AS targetKey, node_slug AS nodeSlug, title, description
                FROM learning_node_links
                WHERE (link_uid = ? OR CAST(id AS TEXT) = ?) AND is_active = 1
                  AND publication_status = 'published'
            """,
            "learning_section": """
                SELECT s.section_uid AS targetKey, m.node_slug AS nodeSlug, s.title, s.description
                FROM learning_material_sections s
                JOIN learning_materials m ON m.id = s.material_id
                WHERE s.section_uid = ? AND s.is_active = 1 AND m.is_active = 1
            """,
        }
        query = queries.get(target_type)
        if not query:
            return None
        with self._connect() as conn:
            params = (target_key, target_key) if target_type in {"learning_material", "learning_link"} else (target_key,)
            return conn.execute(query, params).fetchone()
