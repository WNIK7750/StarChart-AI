def site_tools_href(category: str | None = None) -> str:
    return "tools.html" if not category else f"tools.html?category={category}"
