from fastapi import APIRouter, Query

from app.db.database import db_cursor

router = APIRouter(prefix="/tools", tags=["tools"])

TOOL_META = {
    "chatgpt": {"iconUrl": "https://chatgpt.com/favicon.ico", "description": "OpenAI 通用 AI 助手，覆盖问答、写作、代码、多模态理解和图像生成。"},
    "claude": {"iconUrl": "https://claude.ai/favicon.ico", "description": "Anthropic 长上下文 AI 助手，适合复杂写作、代码审查、资料分析和推理任务。"},
    "deepseek": {"iconUrl": "https://www.deepseek.com/favicon.ico", "description": "深度求索推出的中文友好模型服务，擅长推理、代码和高性价比知识问答。"},
    "kimi": {"iconUrl": "https://kimi.moonshot.cn/favicon.ico", "description": "月之暗面长文本助手，适合论文阅读、资料整理、网页总结和学习问答。"},
    "doubao": {"iconUrl": "https://www.doubao.com/favicon.ico", "description": "字节跳动 AI 助手，覆盖中文对话、写作、图像生成、语音和办公场景。"},
    "jasper": {"iconUrl": "https://www.jasper.ai/favicon.ico", "description": "面向营销团队的 AI 内容平台，可统一品牌语气并生成广告、邮件和社媒文案。"},
    "grammarly": {"iconUrl": "https://www.grammarly.com/favicon.ico", "description": "英文写作助手，提供语法纠错、语气优化、改写建议和团队写作规范。"},
    "copy-ai": {"iconUrl": "https://www.copy.ai/favicon.ico", "description": "销售和营销文案生成工具，适合邮件、落地页、广告创意和增长内容。"},
    "midjourney": {"iconUrl": "https://www.midjourney.com/favicon.ico", "description": "高质量图像生成工具，擅长风格化视觉、概念设计、插画和氛围图。"},
    "canva": {"iconUrl": "https://www.canva.com/favicon.ico", "description": "在线设计平台，内置 AI 图片、文案、排版和社媒素材制作能力。"},
    "adobe-firefly": {"iconUrl": "https://firefly.adobe.com/favicon.ico", "description": "Adobe 创意生态中的生成式设计工具，适合商用友好的图片生成和编辑。"},
    "runway": {"iconUrl": "https://runwayml.com/favicon.ico", "description": "AI 视频创作平台，支持文生视频、图生视频、镜头控制和创意短片制作。"},
    "capcut": {"iconUrl": "https://www.capcut.com/favicon.ico", "description": "剪映国际版，提供短视频剪辑、字幕、模板、特效和 AI 包装能力。"},
    "sora": {"iconUrl": "https://sora.com/favicon.ico", "description": "OpenAI 视频生成工具，面向高质量叙事镜头、动态场景和创意视频生成。"},
    "cursor": {"iconUrl": "https://cursor.com/favicon.ico", "description": "AI 原生代码编辑器，适合项目级代码理解、重构、补全和多文件修改。"},
    "copilot": {"iconUrl": "https://github.com/favicon.ico", "description": "GitHub 官方 AI 编程助手，支持代码补全、解释、测试和 Pull Request 辅助。"},
    "v0": {"iconUrl": "https://v0.dev/favicon.ico", "description": "Vercel 的自然语言前端生成工具，适合快速创建 React 页面和组件原型。"},
    "notebooklm": {"iconUrl": "https://notebooklm.google/favicon.ico", "description": "Google 资料型学习助手，可围绕上传文档生成摘要、问答、提纲和音频概览。"},
    "gamma": {"iconUrl": "https://gamma.app/favicon.ico", "description": "AI 演示文稿与网页文档工具，适合快速生成 PPT、方案页和汇报材料。"},
    "perplexity": {"iconUrl": "https://www.perplexity.ai/favicon.ico", "description": "带来源引用的 AI 搜索引擎，适合资料检索、事实核查和研究型问答。"},
    "tableau": {"iconUrl": "https://www.tableau.com/favicon.ico", "description": "商业智能与数据可视化平台，AI 能力用于洞察解释、自然语言分析和仪表盘。"},
    "suno": {"iconUrl": "https://suno.com/favicon.ico", "description": "AI 音乐生成工具，可根据提示词创作歌曲、旋律、歌词和不同音乐风格。"},
    "elevenlabs": {"iconUrl": "https://elevenlabs.io/favicon.ico", "description": "高质量语音合成和配音平台，支持多语言声音生成、克隆和音频制作。"},
    "zapier": {"iconUrl": "https://zapier.com/favicon.ico", "description": "跨应用自动化平台，可连接常用 SaaS，并用 AI 构建自动化工作流。"},
    "dify": {"iconUrl": "https://dify.ai/favicon.ico", "description": "开源 LLM 应用开发平台，支持工作流、知识库、Agent 和模型编排。"},
}

SIMPLE_ICON_SLUGS = {
    "claude": "anthropic",
    "deepseek": "deepseek",
    "doubao": "bytedance",
    "grammarly": "grammarly",
    "capcut": "capcut",
    "cursor": "cursor",
    "copilot": "githubcopilot",
    "v0": "vercel",
    "gamma": "gamma",
    "perplexity": "perplexity",
    "tableau": "tableau",
    "suno": "suno",
    "elevenlabs": "elevenlabs",
    "zapier": "zapier",
    "dify": "dify",
}


def _fallback_icons(slug: str, official_url: str | None, primary: str | None) -> list[str]:
    fallbacks = []
    if primary:
        fallbacks.append(primary)
    meta_icon = TOOL_META.get(slug, {}).get("iconUrl")
    if meta_icon and meta_icon not in fallbacks:
        fallbacks.append(meta_icon)
    if official_url:
        fallbacks.append(f"https://icons.duckduckgo.com/ip3/{official_url.split('//')[-1].split('/')[0]}.ico")
    return fallbacks


def enrich_tool(row: dict) -> dict:
    meta = TOOL_META.get(row.get("slug"), {})
    simple_slug = SIMPLE_ICON_SLUGS.get(row.get("slug"))
    primary_icon = f"https://cdn.simpleicons.org/{simple_slug}/24292f" if simple_slug else meta.get("iconUrl")
    row["iconUrl"] = primary_icon
    row["iconFallbacks"] = _fallback_icons(row.get("slug", ""), row.get("officialUrl"), primary_icon)
    if meta.get("description"):
        row["description"] = meta["description"]
    return row


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
    return {"items": [enrich_tool(row) for row in rows], "page": page, "pageSize": page_size, "total": total}


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
    return {"items": [enrich_tool(row) for row in rows]}


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
        grouped.setdefault(tool["workflowCode"], []).append(enrich_tool(tool))
    for workflow in workflows:
        workflow["tools"] = grouped.get(workflow["code"], [])
    return {"items": workflows}
