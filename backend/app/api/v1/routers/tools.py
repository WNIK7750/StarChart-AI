from fastapi import APIRouter, Query

from app.services.tool_catalog import (
    latest_tools,
    list_categories,
    list_tools,
    search_tools,
    workflow_suggestions,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/categories")
def get_tool_categories():
    return {"items": list_categories()}


@router.get("/search")
def search_tool_catalog(q: str = "", limit: int = Query(default=7, ge=1, le=30)):
    return {"items": search_tools(q, limit=limit), "query": q}


@router.get("/agent-context")
def get_agent_tool_context(q: str = "", limit: int = Query(default=7, ge=1, le=20)):
    """Compact tool context reserved for Agent retrieval and workflow planning."""
    results = search_tools(q, limit=limit)
    workflows = workflow_suggestions(q, limit=3)
    return {
        "query": q,
        "tools": [
            {
                "id": item["tool"]["id"],
                "name": item["tool"]["name"],
                "description": item["tool"]["description"],
                "categories": item["tool"]["categories"],
                "tags": item["tool"]["tags"],
                "url": item["tool"]["url"],
                "href": item["tool"]["href"],
                "reason": item["reason"],
            }
            for item in results
        ],
        "workflows": workflows,
    }


@router.get("")
def get_tools(
    category: str | None = None,
    subcategory: str | None = None,
    q: str | None = None,
    free_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
):
    return list_tools(category=category, subcategory=subcategory, q=q, free_only=free_only, page=page, page_size=page_size)


@router.get("/latest")
def get_latest_tools(limit: int = Query(default=8, ge=1, le=24)):
    return {"items": latest_tools(limit=limit)}


@router.get("/workflows")
def get_workflows(q: str = "", limit: int = Query(default=3, ge=1, le=12)):
    return {"items": workflow_suggestions(q, limit=limit)}
