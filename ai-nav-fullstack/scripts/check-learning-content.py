import argparse
import sqlite3
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.core.config import DATABASE_PATH
from app.db.database import initialize_database


def online_status(url: str, timeout: float) -> int:
    request = Request(url, method="HEAD", headers={"User-Agent": "ai-nav-content-check/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except Exception as exc:
        return int(getattr(exc, "code", 0) or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate published learning content references.")
    parser.add_argument("--online", action="store_true", help="Also issue HEAD requests to published URLs.")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    initialize_database()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT 'material' AS kind, material_uid AS uid, url
        FROM learning_materials
        WHERE is_active = 1 AND publication_status = 'published'
        UNION ALL
        SELECT 'link' AS kind, link_uid AS uid, url
        FROM learning_node_links
        WHERE is_active = 1 AND publication_status = 'published'
        """
    ).fetchall()
    conn.close()

    errors = []
    seen = set()
    for row in rows:
        key = (row["kind"], row["uid"])
        if not row["uid"]:
            errors.append(f"{row['kind']} has no stable uid")
        elif key in seen:
            errors.append(f"duplicate stable uid: {row['uid']}")
        seen.add(key)
        if urlsplit(row["url"]).scheme not in {"http", "https"}:
            errors.append(f"invalid URL scheme for {row['uid']}: {row['url']}")
        if args.online:
            status = online_status(row["url"], args.timeout)
            if status == 0 or status >= 500:
                errors.append(f"unavailable URL for {row['uid']}: status={status}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Learning content check passed: {len(rows)} published references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
