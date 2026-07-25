import sqlite3

from fastapi import APIRouter, HTTPException

from app.core.config import MIGRATIONS_DIR
from app.db.database import get_connection
from app.platform.navigation import get_navigation_items
from app.platform.schemas import HealthResponse, NavigationResponse, ReadinessResponse

router = APIRouter(tags=["common"])


@router.get("/navigation", response_model=NavigationResponse)
def get_navigation():
    return {"items": get_navigation_items()}


def check_database_ready(conn: sqlite3.Connection, expected_migrations: set[str]) -> dict:
    conn.execute("SELECT 1").fetchone()
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    applied = {row["version"] if isinstance(row, dict) else row[0] for row in rows}
    missing = expected_migrations - applied
    if missing:
        raise RuntimeError(f"Missing migrations: {len(missing)}")
    return {"status": "ready", "migrationCount": len(applied)}


@router.get("/health/live", response_model=HealthResponse)
def health_live():
    return {"status": "ok"}


@router.get("/health/ready", response_model=ReadinessResponse)
def health_ready():
    conn = get_connection()
    try:
        expected = {path.name for path in MIGRATIONS_DIR.glob("*.sql")}
        return check_database_ready(conn, expected)
    except (sqlite3.Error, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "DATABASE_NOT_READY", "message": "数据库尚未准备完成"},
        ) from exc
    finally:
        conn.close()


@router.get("/health", response_model=HealthResponse)
def health_check():
    health_ready()
    return {"status": "ok"}
