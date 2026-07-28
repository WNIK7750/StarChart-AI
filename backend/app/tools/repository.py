import json
from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteToolCatalogRepository:
    def __init__(self, connection_factory: Callable[[], Connection] = get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        conn = self._connection_factory()
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _json(value: str | None) -> list[str]:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []

    def load_catalog(self) -> dict:
        with self._connect() as conn:
            category_rows = conn.execute(
                """
                SELECT code, name, icon, logo_class AS logoClass, description
                FROM tool_categories
                WHERE is_active = 1
                ORDER BY sort_order, id
                """
            ).fetchall()
            subcategory_rows = conn.execute(
                """
                SELECT category_code AS categoryId, name
                FROM tool_subcategories
                WHERE is_active = 1
                ORDER BY category_code, sort_order, id
                """
            ).fetchall()
            tool_rows = conn.execute(
                """
                SELECT slug AS id, name, aliases_json AS aliasesJson, description,
                       mark, official_url AS url, icon_path AS icon,
                       icon_fallbacks_json AS iconFallbacksJson, is_free AS isFree,
                       publication_status AS publicationStatus, link_status AS linkStatus,
                       last_checked_at AS lastCheckedAt
                FROM ai_tools
                WHERE is_active = 1 AND publication_status = 'published'
                ORDER BY sort_order, id
                """
            ).fetchall()
            placements = conn.execute(
                """
                SELECT tool_slug AS toolId, category_code AS categoryId,
                       subcategory_name AS subcategory, heat, tag
                FROM tool_placements placement
                WHERE EXISTS (
                  SELECT 1 FROM ai_tools tool
                  WHERE tool.slug = placement.tool_slug
                    AND tool.is_active = 1 AND tool.publication_status = 'published'
                )
                ORDER BY sort_order, id
                """
            ).fetchall()
            latest_rows = conn.execute(
                """
                SELECT display_name AS displayName, tool_slug AS toolId,
                       provider, label, mark, logo_class AS logoClass
                FROM tool_latest_slots
                WHERE is_active = 1 AND EXISTS (
                  SELECT 1 FROM ai_tools tool
                  WHERE tool.slug = tool_latest_slots.tool_slug
                    AND tool.is_active = 1 AND tool.publication_status = 'published'
                )
                ORDER BY sort_order, id
                """
            ).fetchall()

        subcategories: dict[str, list[str]] = {}
        for row in subcategory_rows:
            subcategories.setdefault(row["categoryId"], ["全部"])
            subcategories[row["categoryId"]].append(row["name"])
        categories = [
            {
                "id": row["code"],
                "name": row["name"],
                "icon": row["icon"],
                "logoClass": row["logoClass"],
                "description": row["description"],
                "subcategories": subcategories.get(row["code"], ["全部"]),
            }
            for row in category_rows
        ]
        tools = [
            {
                "id": row["id"],
                "name": row["name"],
                "aliases": self._json(row["aliasesJson"]),
                "description": row["description"],
                "mark": row["mark"],
                "url": row["url"],
                "icon": row["icon"],
                "iconFallbacks": self._json(row["iconFallbacksJson"]),
                "isFree": bool(row["isFree"]),
                "publicationStatus": row["publicationStatus"],
                "linkStatus": row["linkStatus"],
                "lastCheckedAt": row["lastCheckedAt"],
            }
            for row in tool_rows
        ]
        names = {tool["id"]: tool["name"] for tool in tools}
        latest_tools = [
            {
                "displayName": row["displayName"],
                "toolName": names.get(row["toolId"], row["displayName"]),
                "provider": row["provider"],
                "label": row["label"],
                "mark": row["mark"],
                "logoClass": row["logoClass"],
            }
            for row in latest_rows
        ]
        return {
            "version": 3,
            "categories": categories,
            "tools": tools,
            "placements": placements,
            "latestTools": latest_tools,
        }
