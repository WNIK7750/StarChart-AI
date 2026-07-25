from app.db.database import db_cursor


def get_navigation_items() -> list[dict]:
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT code, label, href
            FROM navigation_items
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
    return [dict(row) for row in rows]
