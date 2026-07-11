from app.services.tool_catalog import search_tools, workflow_suggestions


def site_tools_href(category: str | None = None) -> str:
    return "tools.html" if not category else f"tools.html?category={category}"


def search_tool_cards(query: str, limit: int = 5) -> list[dict]:
    """Return site-safe tool cards for Agent answers."""
    return [
        {
            "type": "tool",
            "title": item["title"],
            "description": item["tool"]["description"],
            "href": item["tool"]["href"],
            "reason": item["reason"],
            "officialUrl": item["tool"]["url"],
        }
        for item in search_tools(query, limit=limit)
    ]


def suggest_workflow(query: str, limit: int = 3) -> list[dict]:
    """Return workflow building blocks grounded in the tool catalog."""
    return [
        {
            "code": workflow["code"],
            "title": workflow["title"],
            "description": workflow["description"],
            "tools": [
                {
                    "id": tool["id"],
                    "name": tool["name"],
                    "href": tool["href"],
                    "officialUrl": tool["url"],
                }
                for tool in workflow["tools"]
            ],
        }
        for workflow in workflow_suggestions(query, limit=limit)
    ]
