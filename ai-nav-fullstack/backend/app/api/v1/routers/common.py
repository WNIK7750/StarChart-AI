from fastapi import APIRouter

from app.db.database import db_cursor

router = APIRouter(tags=["common"])


@router.get("/navigation")
def get_navigation():
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT code, label, href
            FROM navigation_items
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
    return {"items": rows}


@router.get("/health")
def health_check():
    return {"status": "ok"}
