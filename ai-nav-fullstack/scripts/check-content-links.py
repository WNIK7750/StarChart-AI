import argparse
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "database" / "ai_nav.sqlite3"
VALID_LINK_STATUSES = {"unchecked", "healthy", "degraded", "unavailable"}


@dataclass(frozen=True)
class LinkTarget:
    domain: str
    table: str
    key_column: str
    key: str
    url: str
    current_status: str


@dataclass(frozen=True)
class LinkResult:
    target: LinkTarget
    http_status: int
    link_status: str
    detail: str = ""


def classify_http_status(status: int) -> str:
    if 200 <= status < 400:
        return "healthy"
    if status == 0 or status in {401, 403, 405, 408, 425, 429} or status >= 500:
        return "degraded"
    return "unavailable"


def probe_url(url: str, timeout: float) -> tuple[int, str]:
    headers = {"User-Agent": "ai-nav-content-check/2.0", "Accept": "text/html,application/xhtml+xml,*/*"}
    try:
        with urlopen(Request(url, method="HEAD", headers=headers), timeout=timeout) as response:
            return int(response.status), ""
    except HTTPError as error:
        if error.code not in {405, 501}:
            return int(error.code), str(error.reason or "")
    except (URLError, TimeoutError, OSError) as error:
        return 0, str(error.reason if isinstance(error, URLError) else error)

    try:
        with urlopen(Request(url, method="GET", headers={**headers, "Range": "bytes=0-0"}), timeout=timeout) as response:
            return int(response.status), ""
    except HTTPError as error:
        return int(error.code), str(error.reason or "")
    except (URLError, TimeoutError, OSError) as error:
        return 0, str(error.reason if isinstance(error, URLError) else error)


def load_targets(database: Path) -> list[LinkTarget]:
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT 'learning' AS domain_name, 'learning_materials' AS table_name,
                   'material_uid' AS key_column, material_uid AS item_key,
                   url, link_status
            FROM learning_materials
            WHERE is_active = 1 AND publication_status = 'published'
            UNION ALL
            SELECT 'learning', 'learning_node_links', 'link_uid', link_uid,
                   url, link_status
            FROM learning_node_links
            WHERE is_active = 1 AND publication_status = 'published'
            UNION ALL
            SELECT 'tools', 'ai_tools', 'slug', slug, official_url, link_status
            FROM ai_tools
            WHERE is_active = 1 AND publication_status = 'published'
            ORDER BY domain_name, table_name, item_key
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        LinkTarget(row["domain_name"], row["table_name"], row["key_column"], row["item_key"], row["url"], row["link_status"])
        for row in rows
    ]


def validate_targets(targets: list[LinkTarget]) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for target in targets:
        identity = (target.table, target.key)
        if not target.key:
            errors.append(f"{target.table} contains an item without a stable key")
        elif identity in seen:
            errors.append(f"duplicate content key: {target.table}.{target.key}")
        seen.add(identity)
        if urlsplit(target.url).scheme not in {"http", "https"}:
            errors.append(f"invalid URL scheme: {target.table}.{target.key} -> {target.url}")
        if target.current_status not in VALID_LINK_STATUSES:
            errors.append(f"invalid link status: {target.table}.{target.key} -> {target.current_status}")
    return errors


def check_online(target: LinkTarget, timeout: float) -> LinkResult:
    status, detail = probe_url(target.url, timeout)
    return LinkResult(target, status, classify_http_status(status), detail)


def write_results(database: Path, results: list[LinkResult], checked_at: str | None = None) -> None:
    timestamp = checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = sqlite3.connect(database)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for result in results:
            timestamp_column = "last_verified_at" if result.target.table == "learning_materials" else "last_checked_at"
            conn.execute(
                f'UPDATE "{result.target.table}" SET link_status = ?, "{timestamp_column}" = ?, updated_at = CURRENT_TIMESTAMP '
                f'WHERE "{result.target.key_column}" = ?',
                (result.link_status, timestamp, result.target.key),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def summary(targets: list[LinkTarget], results: list[LinkResult] | None = None) -> dict:
    report = {
        "references": len(targets),
        "domains": {
            domain: sum(1 for target in targets if target.domain == domain)
            for domain in sorted({target.domain for target in targets})
        },
    }
    if results is not None:
        report["statuses"] = {
            status: sum(1 for result in results if result.link_status == status)
            for status in sorted(VALID_LINK_STATUSES - {"unchecked"})
        }
        report["unavailable"] = [
            {
                "target": f"{result.target.table}.{result.target.key}",
                "url": result.target.url,
                "httpStatus": result.http_status,
                "detail": result.detail,
            }
            for result in results
            if result.link_status == "unavailable"
        ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and optionally refresh Learning and Tools link health.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--online", action="store_true", help="Probe published URLs. No network is used by default.")
    parser.add_argument("--write", action="store_true", help="Write probe results; requires --online.")
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.write and not args.online:
        parser.error("--write requires --online")
    if not args.database.exists():
        parser.error(f"database does not exist: {args.database}")

    targets = load_targets(args.database)
    errors = validate_targets(targets)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if not args.online:
        print(json.dumps(summary(targets), ensure_ascii=False, indent=2))
        return 0

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 32))) as pool:
        results = list(pool.map(lambda target: check_online(target, args.timeout), targets))
    if args.write:
        write_results(args.database, results)
    report = summary(targets, results)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["unavailable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
