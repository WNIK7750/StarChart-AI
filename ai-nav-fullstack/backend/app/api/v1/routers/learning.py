from fastapi import APIRouter, HTTPException, Query

from app.db.database import db_cursor

router = APIRouter(prefix="/learning", tags=["learning"])


def format_duration(minutes: int) -> str:
    if minutes <= 0:
        return "待补充"
    hours = minutes / 60
    if hours < 1:
        return f"{minutes} min"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{hours:.1f}h"


@router.get("/roadmap")
def get_roadmap():
    with db_cursor() as cur:
        domains = cur.execute(
            """
            SELECT code, name, color, glow_color AS glowColor, description
            FROM knowledge_domains
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
        levels = cur.execute(
            """
            SELECT code, name, color
            FROM difficulty_levels
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
        nodes = cur.execute(
            """
            SELECT n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode,
                   d.color, n.x, n.y, n.width, n.height, n.is_current AS isCurrent
            FROM roadmap_nodes n
            JOIN difficulty_levels d ON d.code = n.difficulty_code
            WHERE n.is_active = 1
            ORDER BY n.sort_order, n.id
            """
        ).fetchall()
        edges = cur.execute(
            """
            SELECT path_d AS pathD, line_type AS lineType
            FROM roadmap_edges
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
        domain_nodes = cur.execute(
            "SELECT domain_code AS domainCode, node_slug AS nodeSlug FROM roadmap_domain_nodes"
        ).fetchall()

    grouped = {}
    for item in domain_nodes:
        grouped.setdefault(item["domainCode"], []).append(item["nodeSlug"])
    return {
        "domains": domains,
        "difficultyLevels": levels,
        "nodes": nodes,
        "edges": edges,
        "domainNodes": grouped,
        "viewBox": "0 0 1320 430",
    }


@router.get("/resources")
def get_learning_resources(domain: str | None = Query(default=None)):
    params = []
    where = "r.is_active = 1"
    if domain:
        where += """
          AND EXISTS (
            SELECT 1 FROM roadmap_domain_nodes dn
            WHERE dn.node_slug = r.node_slug AND dn.domain_code = ?
          )
        """
        params.append(domain)
    with db_cursor() as cur:
        rows = cur.execute(
            f"""
            SELECT r.slug, r.title, r.description, r.cover_label AS coverLabel,
                   r.cover_text AS coverText, r.cover_theme AS coverTheme,
                   r.href, r.node_slug AS nodeSlug
            FROM learning_resources r
            WHERE {where}
            ORDER BY r.sort_order, r.id
            """,
            params,
        ).fetchall()
    return {"items": rows}


@router.get("/nodes/{slug}")
def get_learning_node(slug: str):
    with db_cursor() as cur:
        node = cur.execute(
            """
            SELECT n.slug, n.title, n.subtitle, n.difficulty_code AS difficultyCode,
                   d.name AS difficultyName, d.color, n.sort_order AS sortOrder
            FROM roadmap_nodes n
            JOIN difficulty_levels d ON d.code = n.difficulty_code
            WHERE n.slug = ? AND n.is_active = 1
            """,
            (slug,),
        ).fetchone()
        if not node:
            raise HTTPException(status_code=404, detail="Learning node not found")
        material = cur.execute(
            """
            SELECT id, title, provider, material_type AS materialType, url, start_url AS startUrl,
                   language, access_type AS accessType, cover_label AS coverLabel, cover_text AS coverText,
                   cover_theme AS coverTheme, description, overview
            FROM learning_materials
            WHERE node_slug = ? AND is_primary = 1 AND is_active = 1
            ORDER BY sort_order, id
            LIMIT 1
            """,
            (slug,),
        ).fetchone()
        if not material:
            raise HTTPException(status_code=404, detail="Learning material not found")
        outline = cur.execute(
            """
            SELECT chapter_no AS chapterNo, section_no AS sectionNo, title,
                   description, duration_minutes AS durationMinutes,
                   source_url AS sourceUrl
            FROM learning_material_sections
            WHERE material_id = ? AND is_active = 1
            ORDER BY sort_order, chapter_no, section_no
            """,
            (material["id"],),
        ).fetchall()
        resources = cur.execute(
            """
            SELECT title, description, url, link_type AS linkType, access_type AS accessType,
                   accent_color AS accentColor
            FROM learning_node_links
            WHERE node_slug = ? AND is_active = 1
            ORDER BY sort_order, id
            """,
            (slug,),
        ).fetchall()
        tags = cur.execute(
            """
            SELECT tag
            FROM learning_node_tags
            WHERE node_slug = ?
            ORDER BY sort_order, tag
            """,
            (slug,),
        ).fetchall()
        previous_node = cur.execute(
            """
            SELECT slug, title
            FROM roadmap_nodes
            WHERE is_active = 1 AND sort_order < ?
            ORDER BY sort_order DESC
            LIMIT 1
            """,
            (node["sortOrder"],),
        ).fetchone()
        next_node = cur.execute(
            """
            SELECT slug, title
            FROM roadmap_nodes
            WHERE is_active = 1 AND sort_order > ?
            ORDER BY sort_order
            LIMIT 1
            """,
            (node["sortOrder"],),
        ).fetchone()

    chapter_count = len({item["chapterNo"] for item in outline})
    section_count = len(outline)
    suggested_minutes = sum(item["durationMinutes"] for item in outline)
    material_id = material.pop("id")
    node.pop("sortOrder", None)

    return {
        "node": node,
        "mainMaterial": material,
        "overview": {
            "title": f"为什么学习「{node['title']}」",
            "body": material["overview"],
        },
        "outline": outline,
        "resources": resources,
        "tags": [item["tag"] for item in tags],
        "stats": {
            "chapterCount": chapter_count,
            "sectionCount": section_count,
            "suggestedMinutes": suggested_minutes,
            "suggestedDuration": format_duration(suggested_minutes),
        },
        "navigation": {
            "previous": previous_node,
            "next": next_node,
        },
        "meta": {
            "sourceMaterialId": material_id,
            "durationRule": "suggestedMinutes is the sum of active learning_material_sections.duration_minutes for the primary material.",
        },
    }
