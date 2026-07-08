from fastapi import APIRouter, Query

from app.db.database import db_cursor

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/categories")
def get_tool_categories():
    with db_cursor() as cur:
        categories = cur.execute(
            """
            SELECT code, name, icon, logo_class AS logoClass, description
            FROM tool_categories
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
        subs = cur.execute(
            """
            SELECT category_code AS categoryCode, name
            FROM tool_subcategories
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
    grouped = {}
    for sub in subs:
        grouped.setdefault(sub["categoryCode"], ["全部"]).append(sub["name"])
    for category in categories:
        category["subcategories"] = grouped.get(category["code"], ["全部"])
    return {"items": categories}


@router.get("")
def list_tools(
    category: str | None = None,
    subcategory: str | None = None,
    q: str | None = None,
    free_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
):
    where = ["t.is_active = 1"]
    params: list[str | int] = []
    if category:
        where.append("t.category_code = ?")
        params.append(category)
    if subcategory and subcategory != "全部":
        where.append("t.subcategory_name = ?")
        params.append(subcategory)
    if q:
        where.append("(t.name LIKE ? OR t.description LIKE ? OR c.name LIKE ?)")
        keyword = f"%{q}%"
        params.extend([keyword, keyword, keyword])
    if free_only:
        where.append("t.is_free = 1")

    where_sql = " AND ".join(where)
    offset = (page - 1) * page_size
    with db_cursor() as cur:
        total = cur.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM ai_tools t
            JOIN tool_categories c ON c.code = t.category_code
            WHERE {where_sql}
            """,
            params,
        ).fetchone()["total"]
        rows = cur.execute(
            f"""
            SELECT t.slug, t.name, t.description, t.mark, t.tag, t.official_url AS officialUrl,
                   t.is_free AS isFree, t.is_latest AS isLatest,
                   t.subcategory_name AS subcategory,
                   c.code AS categoryCode, c.name AS categoryName, c.logo_class AS logoClass
            FROM ai_tools t
            JOIN tool_categories c ON c.code = t.category_code
            WHERE {where_sql}
            ORDER BY c.sort_order, t.sort_order, t.id
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    return {"items": rows, "page": page, "pageSize": page_size, "total": total}


@router.get("/latest")
def get_latest_tools(limit: int = Query(default=8, ge=1, le=24)):
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT t.slug, t.name, t.description, t.mark, t.tag,
                   c.logo_class AS logoClass, t.official_url AS officialUrl
            FROM ai_tools t
            JOIN tool_categories c ON c.code = t.category_code
            WHERE t.is_active = 1 AND t.is_latest = 1
            ORDER BY t.sort_order, t.id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"items": rows}


@router.get("/workflows")
def get_workflows():
    with db_cursor() as cur:
        workflows = cur.execute(
            """
            SELECT code, title, description, badge
            FROM tool_workflows
            WHERE is_active = 1
            ORDER BY sort_order, id
            """
        ).fetchall()
        tools = cur.execute(
            """
            SELECT wt.workflow_code AS workflowCode, t.slug, t.name, t.mark
            FROM workflow_tools wt
            JOIN ai_tools t ON t.slug = wt.tool_slug
            ORDER BY wt.sort_order
            """
        ).fetchall()
    grouped = {}
    for tool in tools:
        grouped.setdefault(tool["workflowCode"], []).append(tool)
    for workflow in workflows:
        workflow["tools"] = grouped.get(workflow["code"], [])
    return {"items": workflows}
