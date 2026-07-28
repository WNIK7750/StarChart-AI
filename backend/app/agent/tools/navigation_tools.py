from app.platform.navigation import get_navigation_items


PAGE_DETAILS = {
    "home": {
        "description": "返回站点主页、全站搜索和主要内容入口。",
        "keywords": "主页 首页 回首页 home",
    },
    "learn": {
        "description": "打开学习路线、知识地图和学习节点。",
        "keywords": "学习 路线 知识地图 课程 learn",
    },
    "tools": {
        "description": "打开 AI 工具目录、分类、搜索和工作流推荐。",
        "keywords": "工具 导航 目录 推荐 tools",
    },
    "assistant": {
        "description": "打开站内 AI 学习助手。",
        "keywords": "助手 agent 问答 工作流 assistant",
    },
}
USER_SPACE_PAGE = {
    "code": "settings",
    "label": "用户空间",
    "href": "settings.html",
    "description": "查看账号、学习记录、收藏、工作流和隐私设置。",
    "keywords": "用户空间 设置 账号 个人资料 学习记录 收藏 工作流 隐私 settings",
}


def search_navigation_cards(query: str, limit: int = 5) -> list[dict]:
    pages = [
        {
            **item,
            **PAGE_DETAILS.get(
                item["code"],
                {"description": f"打开{item['label']}页面。", "keywords": item["label"]},
            ),
        }
        for item in get_navigation_items()
    ]
    pages.append(USER_SPACE_PAGE)
    normalized = "".join(query.lower().split())
    matches = [
        page
        for page in pages
        if not normalized
        or normalized in "".join(f"{page['label']} {page['keywords']}".lower().split())
        or any(token and token in normalized for token in page["keywords"].lower().split())
    ]
    selected = (matches or pages)[: max(1, min(limit, 8))]
    return [
        {
            "type": "page",
            "sourceKey": page["code"],
            "title": page["label"],
            "description": page["description"],
            "href": page["href"],
            "reason": "站内页面",
        }
        for page in selected
    ]
