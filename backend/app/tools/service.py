from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.tools.repository import SQLiteToolCatalogRepository

QUERY_EXPANSIONS: dict[str, str] = {
    "企业": "企业 公司 团队 商业化 安全 隐私 合规 私有化 权限 协作 enterprise business security privacy compliance copilot tabnine sentry glean notion",
    "企业级": "企业 公司 团队 商业化 安全 隐私 合规 私有化 权限 协作 enterprise business security privacy compliance copilot tabnine sentry glean notion",
    "公司": "企业 团队 协作 办公 安全 权限",
    "团队": "企业 协作 办公 会议 文档 工作流",
    "安全": "隐私 合规 权限 代码审查 测试 运维 sentry snyk",
    "私有化": "企业 安全 隐私 本地 部署",
    "代码": "编程 开发 ide copilot cursor code tabnine claude code",
    "编程": "代码 开发 ide copilot cursor code tabnine",
    "写作": "文本 文案 论文 公文 翻译",
    "画图": "绘画 图像 设计 生图 修图",
    "视频": "剪辑 数字人 文生视频 配音 音乐",
    "搜索": "检索 研究 资料 问答 数据",
    "论文": "研究 学术 文献 引用 阅读",
    "阅读": "论文 文献 资料 pdf 文档 总结 问答 notebooklm chatdoc chatpdf",
    "自动化": "工作流 办公 连接器 zapier make",
    "工作流": "workflow agent 自动化 工具组合",
    "国产": "国内 中文 中国 内网 大模型",
}

PINYIN_ALIASES: dict[str, str] = {
    "doubao": "豆包 字节跳动",
    "tongyi": "通义 千问 万相 灵码 阿里",
    "wenxin": "文心 百度 一言 一格",
    "kimi": "月之暗面 长文本",
    "yuanbao": "腾讯 元宝",
    "deepseek": "深度求索 国产 大模型",
    "jianying": "剪映 capcut",
    "jimeng": "即梦 字节跳动",
    "kling": "可灵 快手",
    "quark": "夸克 阿里 搜索 ppt",
    "metaso": "秘塔 搜索",
}

RECOMMENDED_TOOL_NAMES = ["ChatGPT", "DeepSeek", "Claude", "豆包", "Cursor", "Google NotebookLM", "Perplexity"]

INTENT_TOOL_BOOSTS = [
    (re.compile(r"code|代码|编程|开发|ide", re.I), ["Cursor", "GitHub Copilot", "Claude Code", "Tabnine", "CodeBuddy", "Codeium", "通义灵码", "Trae"]),
    (re.compile(r"企业|公司|团队|商业|enterprise|安全|合规|私有", re.I), ["Tabnine", "Glean", "钉钉 AI 助理", "Microsoft Copilot", "Notion AI", "GitHub Copilot", "Sentry", "Snyk AI"]),
    (re.compile(r"论文|学术|研究|文献", re.I), ["Google NotebookLM", "Perplexity", "Consensus", "Elicit", "Scite", "ChatDOC"]),
    (re.compile(r"自动化|工作流|workflow", re.I), ["Zapier AI", "Make", "Coze 扣子", "Gumloop", "Flowith"]),
]

STOP_TERMS = {"的", "了", "呢", "吗", "啊", "吧", "和", "与", "及", "或", "在", "是", "有", "用", "找", "搜", "查看", "我要", "想", "做", "个", "一个", "一种", "什么", "如何", "怎么"}


def compact(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def terms(value: str | None) -> list[str]:
    raw = str(value or "").lower()
    latin = re.findall(r"[a-z0-9.+#-]+", raw)
    cjk = re.findall(r"[\u4e00-\u9fa5]{1,}", raw)
    cjk_terms: list[str] = []
    for word in cjk:
        if len(word) <= 2:
            cjk_terms.append(word)
        else:
            cjk_terms.append(word)
            cjk_terms.extend(word[index : index + 2] for index in range(len(word) - 1))
    return list(dict.fromkeys([term for term in [*latin, *cjk_terms] if term]))


def expand_query(query: str | None) -> dict[str, Any]:
    raw = str(query or "").strip().lower()
    base_terms = terms(raw)
    extra: list[str] = []
    known_keys = [*QUERY_EXPANSIONS.keys(), *PINYIN_ALIASES.keys(), "code", "ide", "agent", "workflow", "rag", "prompt", "llm", "ppt", "pdf"]
    remainder = raw
    for key in sorted(known_keys, key=len, reverse=True):
        remainder = remainder.replace(key.lower(), "")
    for key, value in QUERY_EXPANSIONS.items():
        if key.lower() in raw or key in base_terms:
            extra.append(value)
    for key, value in PINYIN_ALIASES.items():
        if key in raw:
            extra.append(value)
    return {
        "raw": raw,
        "compact": compact(raw),
        "terms": list(dict.fromkeys([*base_terms, *terms(" ".join(extra))])),
        "direct_terms": base_terms,
        "is_known_intent": raw in {key.lower() for key in QUERY_EXPANSIONS} or raw in PINYIN_ALIASES or re.match(r"^(code|ide|agent|workflow|rag|prompt|llm|ppt|pdf)$", raw, re.I) is not None or (bool(raw) and len(remainder) == 0),
    }


def _tool_heat(tool_id: str, placements: list[dict[str, Any]]) -> int:
    return max([0, *[int(place.get("heat") or 0) for place in placements if place.get("toolId") == tool_id]])


def _category_maps(categories: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {category["id"]: category for category in categories}


def _enrich_text(item: dict[str, Any]) -> dict[str, Any]:
    text = f"{item.get('title', '')} {item.get('description', '')} {item.get('keywords', '')}"
    return {
        **item,
        "_title": compact(item.get("title")),
        "_description": compact(item.get("description")),
        "_keywords": compact(item.get("keywords")),
        "_all_text": compact(text),
        "_term_text": " ".join(terms(text)),
    }


def _to_public_tool(tool: dict[str, Any], placements: list[dict[str, Any]], categories: dict[str, dict[str, Any]]) -> dict[str, Any]:
    own_placements = [place for place in placements if place.get("toolId") == tool["id"]]
    category_names = list(dict.fromkeys([categories.get(place.get("categoryId"), {}).get("name") for place in own_placements if categories.get(place.get("categoryId"))]))
    subcategories = list(dict.fromkeys([place.get("subcategory") for place in own_placements if place.get("subcategory")]))
    tags = list(dict.fromkeys([place.get("tag") for place in own_placements if place.get("tag")]))
    return {
        "id": tool["id"],
        "name": tool["name"],
        "aliases": tool.get("aliases", []),
        "description": tool.get("description", ""),
        "mark": tool.get("mark", tool["name"][:2]),
        "url": tool.get("url", ""),
        "icon": tool.get("icon", ""),
        "iconFallbacks": tool.get("iconFallbacks", []),
        "isFree": bool(tool.get("isFree")),
        "publicationStatus": tool.get("publicationStatus", "published"),
        "linkStatus": tool.get("linkStatus", "unchecked"),
        "lastCheckedAt": tool.get("lastCheckedAt"),
        "categories": category_names,
        "subcategories": subcategories,
        "tags": tags,
        "heat": _tool_heat(tool["id"], placements),
        "href": f"tools.html?q={tool['name']}#directory",
    }


@lru_cache(maxsize=1)
def get_tool_catalog() -> dict[str, Any]:
    data = SQLiteToolCatalogRepository().load_catalog()
    categories = _category_maps(data.get("categories", []))
    tools = [_to_public_tool(tool, data.get("placements", []), categories) for tool in data.get("tools", [])]
    search_items = [
        _enrich_text(
            {
                "source": "tool",
                "type": "工具",
                "title": tool["name"],
                "description": f"{'、'.join(tool['categories']) or 'AI 工具'} · {tool['description']}",
                "url": tool["href"],
                "iconUrl": tool["icon"],
                "iconFallbacks": tool["iconFallbacks"],
                "mark": tool["mark"],
                "heat": tool["heat"],
                "tool": tool,
                "keywords": " ".join([tool["name"], *tool["aliases"], tool["description"], *tool["categories"], *tool["subcategories"], *tool["tags"], tool["url"]]),
            }
        )
        for tool in tools
    ]
    return {
        "version": data.get("version", 1),
        "categories": data.get("categories", []),
        "placements": data.get("placements", []),
        "tools": tools,
        "latestTools": data.get("latestTools", []),
        "searchItems": search_items,
    }


def clear_tool_catalog_cache() -> None:
    get_tool_catalog.cache_clear()


def catalog_snapshot() -> dict[str, Any]:
    catalog = get_tool_catalog()
    return {
        "version": catalog["version"],
        "categories": catalog["categories"],
        "tools": catalog["tools"],
        "placements": catalog["placements"],
        "latestTools": catalog["latestTools"],
        "meta": {"source": "tools.database", "contractVersion": 1},
    }


def meaningful_direct_terms(query: dict[str, Any]) -> list[str]:
    return [
        term
        for term in [compact(term) for term in query["direct_terms"]]
        if len(term) >= 2 and term not in STOP_TERMS and (term != query["compact"] or len(term) <= 5)
    ]


def direct_match_count(item: dict[str, Any], query: dict[str, Any]) -> int:
    return sum(1 for term in meaningful_direct_terms(query) if term in item["_title"] or term in item["_keywords"] or term in item["_description"])


def reason_for(item: dict[str, Any], query: dict[str, Any]) -> str:
    if not query["raw"]:
        return "推荐"
    direct = [compact(term) for term in query["direct_terms"]]
    if item["_title"] == query["compact"]:
        return "精确匹配"
    if item["_title"].startswith(query["compact"]):
        return "名称前缀"
    if any(term in item["_keywords"] for term in direct):
        return "关键词"
    if any(term in item["_description"] for term in direct):
        return "描述相关"
    return "相关推荐"


def score_result(item: dict[str, Any], query: dict[str, Any]) -> float:
    if not query["raw"]:
        if item["title"] in RECOMMENDED_TOOL_NAMES:
            return 120 - RECOMMENDED_TOOL_NAMES.index(item["title"])
        return 48 + (item.get("heat") or 0) / 8

    q = query["compact"]
    direct = [compact(term) for term in query["direct_terms"]]
    score = 0.0
    if item["_title"] == q:
        score += 260
    if item["_title"].startswith(q):
        score += 180
    if q and q in item["_title"]:
        score += 135
    if q and q in item["_keywords"]:
        score += 90
    if q and q in item["_description"]:
        score += 45
    for term in query["terms"]:
        term = compact(term)
        if not term:
            continue
        weight = 1 if term in direct else 0.42
        if term in item["_title"]:
            score += 38 * weight
        if term in item["_keywords"]:
            score += 22 * weight
        if term in item["_description"]:
            score += 12 * weight
        if term in item["_term_text"]:
            score += 8 * weight
    if score > 0:
        score += 6 + min(18, (item.get("heat") or 0) / 6)
    if "国产" in query["raw"] and re.search(r"国产|国内|中文|中国|阿里|百度|腾讯|字节|月之暗面|深度求索", item["keywords"], re.I):
        score += 70
    for matcher, names in INTENT_TOOL_BOOSTS:
        if matcher.search(query["raw"]) and item["title"] in names:
            score += 90 - names.index(item["title"]) * 5
    return score


def is_acceptable_match(item: dict[str, Any], query: dict[str, Any]) -> bool:
    if not query["raw"]:
        return True
    if item["score"] <= 18:
        return False
    if query["is_known_intent"]:
        return True
    direct = meaningful_direct_terms(query)
    if not direct:
        return item["score"] >= 80
    matched = item.get("directMatches", 0)
    if len(direct) <= 2:
        return matched >= 1
    return matched >= min(2, -(-len(direct) // 2))


def search_tools(query_text: str | None, limit: int = 7) -> list[dict[str, Any]]:
    query = expand_query(query_text)
    results = []
    for item in get_tool_catalog()["searchItems"]:
        score = score_result(item, query)
        candidate = {
            **item,
            "score": score,
            "directMatches": direct_match_count(item, query),
        }
        candidate["reason"] = reason_for(candidate, query)
        if is_acceptable_match(candidate, query):
            results.append(candidate)
    results.sort(key=lambda item: (-item["score"], -(item.get("heat") or 0), item["title"]))
    return [public_search_result(item) for item in results[:limit]]


def focus_task_query(query: str | None) -> str:
    focused = str(query or "")
    for token in ["帮我", "我想", "我要", "做一个", "生成", "推荐", "工作流", "流程", "方案", "工具组合"]:
        focused = focused.replace(token, " ")
    return re.sub(r"\s+", " ", focused).strip() or str(query or "")


def public_search_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": item["type"],
        "title": item["title"],
        "description": item["description"],
        "href": item["url"],
        "iconUrl": item.get("iconUrl"),
        "iconFallbacks": item.get("iconFallbacks", []),
        "mark": item.get("mark"),
        "score": round(float(item["score"]), 2),
        "reason": item["reason"],
        "tool": item["tool"],
    }


def list_categories() -> list[dict[str, Any]]:
    return get_tool_catalog()["categories"]


def list_tools(category: str | None = None, subcategory: str | None = None, q: str | None = None, free_only: bool = False, page: int = 1, page_size: int = 12) -> dict[str, Any]:
    tools = get_tool_catalog()["tools"]
    if category:
        category_map = {cat["id"]: cat["name"] for cat in get_tool_catalog()["categories"]}
        category_name = category_map.get(category, category)
        tools = [tool for tool in tools if category_name in tool["categories"] or category in tool["categories"]]
    if subcategory and subcategory != "全部":
        tools = [tool for tool in tools if subcategory in tool["subcategories"]]
    if free_only:
        tools = [tool for tool in tools if tool["isFree"]]
    if q:
        allowed = {result["tool"]["id"] for result in search_tools(q, limit=200)}
        tools = [tool for tool in tools if tool["id"] in allowed]
    start = (page - 1) * page_size
    return {"items": tools[start : start + page_size], "page": page, "pageSize": page_size, "total": len(tools)}


def latest_tools(limit: int = 8) -> list[dict[str, Any]]:
    by_name = {tool["name"]: tool for tool in get_tool_catalog()["tools"]}
    results = []
    for item in get_tool_catalog()["latestTools"]:
        tool = by_name.get(item.get("toolName")) or by_name.get(item.get("displayName"))
        if tool:
            results.append({**item, "tool": tool})
        if len(results) >= limit:
            break
    return results


def workflow_suggestions(query: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    scenarios = [
        {"code": "video-content", "title": "YouTube 视频工作流", "description": "从创意、脚本、画面到成片的一站式 AI 制作链路。", "toolNames": ["ChatGPT", "Midjourney", "Runway"]},
        {"code": "paper-reading", "title": "论文阅读工作流", "description": "高效理解、总结、追问与沉淀资料的学术辅助方案。", "toolNames": ["Google NotebookLM", "Perplexity", "Claude"]},
        {"code": "code-development", "title": "代码开发工作流", "description": "智能编程、协作补全与质量监控的全栈开发组合。", "toolNames": ["Cursor", "GitHub Copilot", "Sentry"]},
    ]
    focused_query = focus_task_query(query)
    if query:
        raw = str(query or "").lower()
        if re.search(r"论文|学术|研究|文献|阅读", raw):
            scenarios.sort(key=lambda item: 0 if item["code"] == "paper-reading" else 1)
        elif re.search(r"代码|编程|开发|code|ide", raw):
            scenarios.sort(key=lambda item: 0 if item["code"] == "code-development" else 1)
        elif re.search(r"视频|剪辑|短片|youtube", raw):
            scenarios.sort(key=lambda item: 0 if item["code"] == "video-content" else 1)
        ranked_tools = search_tools(focused_query, limit=20)
        if focused_query and not ranked_tools:
            return []
        names = {result["tool"]["name"] for result in ranked_tools}
        scenarios.sort(key=lambda item: -sum(1 for name in item["toolNames"] if name in names))
    tools_by_name = {tool["name"]: tool for tool in get_tool_catalog()["tools"]}
    return [
        {
            **scenario,
            "tools": [tools_by_name[name] for name in scenario["toolNames"] if name in tools_by_name],
        }
        for scenario in scenarios[:limit]
    ]
