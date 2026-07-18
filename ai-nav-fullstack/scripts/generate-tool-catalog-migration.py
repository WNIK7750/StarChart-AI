import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "frontend" / "assets" / "js" / "tool-data.js"
LISTS_PATH = ROOT / "frontend" / "assets" / "js" / "tool-page-lists.js"
MIGRATIONS_DIR = ROOT / "database" / "migrations"


def load_assignment(path: Path, variable: str) -> dict:
    source = path.read_text(encoding="utf-8")
    match = re.search(rf"window\.{re.escape(variable)}\s*=\s*(\{{.*?\}})\s*;", source, re.S)
    if not match:
        raise RuntimeError(f"Cannot find window.{variable} in {path}")
    return json.loads(match.group(1))


def sql(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def values(rows: list[list]) -> str:
    return ",\n".join("(" + ", ".join(sql(value) for value in row) + ")" for row in rows)


def load_sources() -> tuple[dict, dict]:
    return (
        load_assignment(DATA_PATH, "AINavToolData"),
        load_assignment(LISTS_PATH, "AINavToolPageLists"),
    )


def validate_catalog(data: dict, lists: dict) -> None:
    tools = data["tools"]
    placements = data["placements"]
    categories = data["categories"]
    if not tools or not placements or not categories:
        raise RuntimeError("Tool catalog must contain categories, tools, and placements")
    category_ids = {category["id"] for category in categories}
    if len(category_ids) != len(categories):
        raise RuntimeError("Category IDs must be unique")
    tool_ids = {tool["id"] for tool in tools}
    if len(tool_ids) != len(tools):
        raise RuntimeError("Tool IDs must be unique")
    if any(place["toolId"] not in tool_ids for place in placements):
        raise RuntimeError("Every placement must reference a known tool")
    if any(place["categoryId"] not in category_ids for place in placements):
        raise RuntimeError("Every placement must reference a known category")
    tool_names = {tool["name"] for tool in tools}
    tool_by_name = {tool["name"]: tool for tool in tools}
    if len(tool_names) != len(tools):
        raise RuntimeError("Tool names must be unique")
    if any(item["toolName"] not in tool_names for item in lists["latestTools"]):
        raise RuntimeError("Every latest slot must reference a known tool")
    if any(not str(tool.get("url", "")).startswith("https://") for tool in tools):
        raise RuntimeError("Every tool must use an HTTPS official URL")
    allowed_publication_statuses = {"draft", "published", "archived"}
    if any(tool.get("publicationStatus", "published") not in allowed_publication_statuses for tool in tools):
        raise RuntimeError("Every tool must use a supported publication status")
    if any(tool_by_name[slot["toolName"]].get("publicationStatus", "published") != "published" for slot in lists["latestTools"]):
        raise RuntimeError("Latest slots must reference published tools")


def build_migration(data: dict | None = None, lists: dict | None = None) -> str:
    if data is None or lists is None:
        data, lists = load_sources()
    validate_catalog(data, lists)
    tools = data["tools"]
    placements = data["placements"]
    categories = data["categories"]

    placements_by_tool: dict[str, list[dict]] = {}
    for place in placements:
        placements_by_tool.setdefault(place["toolId"], []).append(place)
    latest_by_name = {item["toolName"]: item for item in lists["latestTools"]}
    tool_by_name = {tool["name"]: tool for tool in tools}

    category_rows = [
        [category["id"], category["name"], category["icon"], category["logoClass"], category["description"], index * 10, True]
        for index, category in enumerate(categories, 1)
    ]
    subcategory_rows = []
    seen_subcategories = set()
    for category in categories:
        names = [name for name in category.get("subcategories", []) if name != "全部"]
        names.extend(place["subcategory"] for place in placements if place["categoryId"] == category["id"])
        for index, name in enumerate(dict.fromkeys(names), 1):
            key = (category["id"], name)
            if key not in seen_subcategories:
                seen_subcategories.add(key)
                subcategory_rows.append([*key, index * 10, True])

    tool_rows = []
    for index, tool in enumerate(tools, 1):
        own = placements_by_tool[tool["id"]]
        primary = own[0]
        is_free = any(re.search(r"免费|开源|\bfree\b|\bopen(?:\s*source)?\b", str(place.get("tag", "")), re.I) for place in own)
        tool_rows.append([
            tool["id"], primary["categoryId"], primary["subcategory"], tool["name"],
            tool["description"], tool.get("mark") or tool["name"][:2], primary.get("tag", ""),
            tool.get("url", ""), is_free, tool["name"] in latest_by_name, index * 10,
            json.dumps(tool.get("aliases", []), ensure_ascii=False, separators=(",", ":")),
            tool.get("icon", ""),
            json.dumps(tool.get("iconFallbacks", []), ensure_ascii=False, separators=(",", ":")),
            tool.get("publicationStatus", "published"),
        ])
    placement_rows = [
        [place["toolId"], place["categoryId"], place["subcategory"], int(place.get("heat") or 0), place.get("tag", ""), index * 10]
        for index, place in enumerate(placements, 1)
    ]
    latest_rows = []
    for index, item in enumerate(lists["latestTools"], 1):
        tool = tool_by_name[item["toolName"]]
        latest_rows.append([
            tool["id"], item["displayName"], item.get("provider", ""), item.get("label", ""),
            item.get("mark", tool.get("mark", "AI")), item.get("logoClass", "logo-chat"), index * 10,
        ])

    return f"""-- Generated by scripts/generate-tool-catalog-migration.py. Do not edit by hand.
-- Source snapshot: tool-data.js v{data.get('version')} ({len(tools)} tools, {len(placements)} placements).

-- ai-nav:add-column-if-missing ai_tools aliases_json TEXT NOT NULL DEFAULT '[]'
-- ai-nav:add-column-if-missing ai_tools icon_path TEXT NOT NULL DEFAULT ''
-- ai-nav:add-column-if-missing ai_tools icon_fallbacks_json TEXT NOT NULL DEFAULT '[]'

CREATE TABLE IF NOT EXISTS tool_placements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_slug TEXT NOT NULL,
  category_code TEXT NOT NULL,
  subcategory_name TEXT NOT NULL,
  heat INTEGER NOT NULL DEFAULT 0 CHECK (heat BETWEEN 0 AND 100),
  tag TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tool_slug) REFERENCES ai_tools(slug),
  FOREIGN KEY (category_code, subcategory_name) REFERENCES tool_subcategories(category_code, name),
  UNIQUE (tool_slug, category_code, subcategory_name)
);

CREATE INDEX IF NOT EXISTS idx_tool_placements_category
ON tool_placements(category_code, subcategory_name, sort_order);

CREATE INDEX IF NOT EXISTS idx_tool_placements_tool
ON tool_placements(tool_slug, sort_order);

CREATE TABLE IF NOT EXISTS tool_latest_slots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_slug TEXT NOT NULL,
  display_name TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT '',
  label TEXT NOT NULL DEFAULT '',
  mark TEXT NOT NULL DEFAULT 'AI',
  logo_class TEXT NOT NULL DEFAULT 'logo-chat',
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tool_slug) REFERENCES ai_tools(slug),
  UNIQUE (tool_slug)
);

UPDATE tool_categories SET is_active = 0;
INSERT INTO tool_categories(code, name, icon, logo_class, description, sort_order, is_active)
VALUES
{values(category_rows)}
ON CONFLICT(code) DO UPDATE SET
  name = excluded.name, icon = excluded.icon, logo_class = excluded.logo_class,
  description = excluded.description, sort_order = excluded.sort_order, is_active = 1,
  updated_at = CURRENT_TIMESTAMP;

UPDATE tool_subcategories SET is_active = 0;
INSERT INTO tool_subcategories(category_code, name, sort_order, is_active)
VALUES
{values(subcategory_rows)}
ON CONFLICT(category_code, name) DO UPDATE SET
  sort_order = excluded.sort_order, is_active = 1, updated_at = CURRENT_TIMESTAMP;

UPDATE ai_tools SET is_active = 0, is_latest = 0;
INSERT INTO ai_tools(
  slug, category_code, subcategory_name, name, description, mark, tag,
  official_url, is_free, is_latest, sort_order, aliases_json, icon_path,
  icon_fallbacks_json, publication_status, is_active
)
VALUES
{values([row + [True] for row in tool_rows])}
ON CONFLICT(slug) DO UPDATE SET
  category_code = excluded.category_code,
  subcategory_name = excluded.subcategory_name,
  name = excluded.name,
  description = excluded.description,
  mark = excluded.mark,
  tag = excluded.tag,
  official_url = excluded.official_url,
  is_free = excluded.is_free,
  is_latest = excluded.is_latest,
  sort_order = excluded.sort_order,
  aliases_json = excluded.aliases_json,
  icon_path = excluded.icon_path,
  icon_fallbacks_json = excluded.icon_fallbacks_json,
  publication_status = excluded.publication_status,
  is_active = 1,
  updated_at = CURRENT_TIMESTAMP;

DELETE FROM tool_placements;
INSERT INTO tool_placements(tool_slug, category_code, subcategory_name, heat, tag, sort_order)
VALUES
{values(placement_rows)};

DELETE FROM tool_latest_slots;
INSERT INTO tool_latest_slots(tool_slug, display_name, provider, label, mark, logo_class, sort_order)
VALUES
{values(latest_rows)};
"""


def migration_version(path: Path) -> int:
    match = re.match(r"(\d{3})_", path.name)
    if not match:
        raise RuntimeError("Migration filename must start with a three-digit version")
    return int(match.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a new append-only tool catalog migration")
    parser.add_argument("--output", required=True, type=Path, help="New migration path, for example database/migrations/012_tool_catalog_refresh.sql")
    args = parser.parse_args()
    output_path = args.output.resolve()
    migrations_dir = MIGRATIONS_DIR.resolve()
    if output_path.parent != migrations_dir:
        raise RuntimeError(f"Output must be written directly under {migrations_dir}")
    if output_path.exists():
        raise RuntimeError(f"Refusing to overwrite existing migration: {output_path.name}")
    requested_version = migration_version(output_path)
    existing_versions = [migration_version(path) for path in MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")]
    if existing_versions and requested_version <= max(existing_versions):
        raise RuntimeError(f"Migration version must be greater than {max(existing_versions):03d}")
    source = build_migration()
    output_path.write_text(source, encoding="utf-8", newline="\n")
    print(f"Wrote {output_path} ({len(source)} bytes)")


if __name__ == "__main__":
    main()
