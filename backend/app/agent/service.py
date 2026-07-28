import re

from app.agent.evaluator import validate_response
from app.agent.router import classify_intent
from app.agent.schemas import (
    AgentChatRequest,
    AgentCitation,
    AgentLinkCard,
    AgentPageContext,
    AgentResponseMeta,
    AgentStructuredResponse,
    AgentToolCall,
    AgentUserContextMeta,
    AgentWorkflowDraft,
    AgentWorkflowDraftStep,
    AgentWorkflowStep,
)
from app.agent.tools.catalog_tools import search_tool_cards, suggest_workflow
from app.agent.tools.learning_tools import search_learning_cards
from app.agent.tools.navigation_tools import search_navigation_cards


READ_CAPABILITIES_BY_INTENT = {
    "qa": {"learning.search", "tools.search"},
    "navigation": {"navigation.read"},
    "tool_recommendation": {"tools.search"},
    "workflow_generation": {"tools.search", "tools.workflow"},
    "learning_plan": {"learning.search"},
}
CONTEXT_REFERENCE_PHRASES = {
    "这个",
    "这个是什么",
    "这个内容",
    "这个内容是什么",
    "这个分类",
    "这个分类是什么",
    "当前页面",
    "当前内容",
    "这里",
}

COMMON_QUERY_SCAFFOLDING = (
    "请给我介绍一下",
    "给我一条",
    "请介绍一下",
    "介绍一下",
    "请介绍",
    "是什么",
    "请说明",
    "告诉我",
    "如何学习",
    "怎么学",
    "如何学",
    "学习路线",
    "学习计划",
    "帮我",
    "我要",
    "我想",
    "做",
)
INTENT_QUERY_SCAFFOLDING = {
    "tool_recommendation": (
        "推荐一个",
        "推荐一种",
        "推荐一些",
        "推荐",
        "哪个工具",
        "哪款工具",
        "什么工具",
        "帮我找",
        "选择",
        "我该",
        "哪款",
        "一款",
        "适合",
        "一个",
        "一种",
        "工具",
    ),
    "workflow_generation": (
        "设计一套",
        "给我一个",
        "生成一个",
        "制定一个",
        "工作流",
        "流程",
        "方案",
        "工具组合",
        "设计",
        "生成",
        "制定",
    ),
    "navigation": ("怎么打开", "如何打开", "跳转到", "带我去", "去往", "在哪里", "在哪儿", "打开", "前往"),
}


def _uses_page_reference(message: str) -> bool:
    compact = "".join(message.lower().split()).strip("，。！？；：、,.!?;:")
    if compact in CONTEXT_REFERENCE_PHRASES:
        return True
    reference_tokens = ("这个工具", "当前节点", "当前分类")
    if not any(token in compact for token in reference_tokens):
        return False
    remainder = compact
    for token in (
        *reference_tokens,
        "请问",
        "请",
        "如何",
        "怎么",
        "怎样",
        "使用",
        "介绍",
        "说明",
        "是什么",
        "有什么",
        "告诉我",
        "一下",
    ):
        remainder = remainder.replace(token, "")
    return not remainder


def plan_read_capabilities(request: AgentChatRequest, intent: str) -> set[str]:
    capabilities = set(READ_CAPABILITIES_BY_INTENT[intent])
    if intent != "qa" or not _uses_page_reference(request.message):
        return capabilities
    page = (request.pageContext.page or "").lower()
    if request.pageContext.nodeSlug or page in {"learn", "learn-node"}:
        return {"learning.search"}
    if request.pageContext.toolCategory or page == "tools":
        return {"tools.search"}
    return capabilities


def agent_retrieval_query(
    message: str,
    intent: str | None = None,
    page_context: AgentPageContext | None = None,
) -> str:
    resolved_intent = intent or classify_intent(message)
    focused = message
    scaffolding = [
        *COMMON_QUERY_SCAFFOLDING,
        *INTENT_QUERY_SCAFFOLDING.get(resolved_intent, ()),
    ]
    for token in sorted(set(scaffolding), key=len, reverse=True):
        focused = focused.replace(token, " ")
    focused = re.sub(r"[，。！？；：、,.!?;:]+", " ", focused)
    cleaned = " ".join(focused.split())
    if page_context and _uses_page_reference(message):
        context_hint = page_context.nodeSlug or page_context.toolCategory
        if context_hint:
            return context_hint
    if cleaned:
        return cleaned
    return "AI" if resolved_intent == "tool_recommendation" else ""


def needs_user_context(request: AgentChatRequest) -> bool:
    return classify_intent(request.message) in {"tool_recommendation", "workflow_generation"}


def draft_agent_response(request: AgentChatRequest, user_context: dict | None = None) -> AgentStructuredResponse:
    """Deterministic Agent foundation grounded in site data.

    This is not the final LLM orchestration layer. It deliberately keeps
    retrieval, link cards, workflow candidates, and response validation behind
    stable module boundaries so a later model call can be inserted without
    rewriting the tool catalog or API contracts.
    """
    intent = classify_intent(request.message)
    retrieval_query = agent_retrieval_query(request.message, intent, request.pageContext)
    capabilities = plan_read_capabilities(request, intent)
    tool_cards = (
        search_tool_cards(retrieval_query, limit=5)
        if "tools.search" in capabilities
        else []
    )
    learning_cards = (
        search_learning_cards(retrieval_query, limit=5)
        if "learning.search" in capabilities
        else []
    )
    page_cards = (
        search_navigation_cards(retrieval_query, limit=5)
        if "navigation.read" in capabilities
        else []
    )
    preferences = (user_context or {}).get("preferences", {})
    if preferences.get("freeFirst") or preferences.get("cnFirst"):
        tool_cards.sort(
            key=lambda card: (
                -int(preferences.get("freeFirst", False) and card.get("isFree", False)),
                -int(
                    preferences.get("cnFirst", False)
                    and bool({"国产", "国内", "中文"} & set(card["tags"]))
                ),
            )
        )
    workflows = (
        suggest_workflow(retrieval_query, limit=1)
        if "tools.workflow" in capabilities
        else []
    )

    if intent in {"tool_recommendation", "workflow_generation"}:
        ordered_cards = [*tool_cards, *learning_cards, *page_cards]
    elif intent == "navigation":
        ordered_cards = [*page_cards, *learning_cards, *tool_cards]
    else:
        ordered_cards = [*learning_cards, *tool_cards, *page_cards]

    citations = [
        AgentCitation(
            citationId=f"{card['type']}:{card['sourceKey']}",
            sourceType=card["type"],
            sourceKey=card["sourceKey"],
            title=card["title"],
            href=card["href"],
        )
        for card in ordered_cards
    ]
    citation_ids = {citation.citationId for citation in citations}
    for workflow in workflows:
        for tool in workflow["tools"]:
            citation_id = f"tool:{tool['id']}"
            if citation_id not in citation_ids:
                citations.append(
                    AgentCitation(
                        citationId=citation_id,
                        sourceType="tool",
                        sourceKey=tool["id"],
                        title=tool["name"],
                        href=tool["href"],
                    )
                )
                citation_ids.add(citation_id)

    cards = [
        AgentLinkCard(
            type=card["type"],
            sourceKey=card["sourceKey"],
            title=card["title"],
            description=card["description"],
            href=card["href"],
            reason=card.get("reason"),
            citationIds=[f"{card['type']}:{card['sourceKey']}"],
        )
        for card in ordered_cards
    ]

    workflow_steps: list[AgentWorkflowStep] = []
    if workflows:
        workflow_steps = [
            AgentWorkflowStep(
                order=index + 1,
                name=tool["name"],
                objective=f"用于{workflows[0]['title']}中的第 {index + 1} 步。",
                toolSlugs=[tool["id"]],
                targetHref=tool["href"],
                citationIds=[f"tool:{tool['id']}"],
            )
            for index, tool in enumerate(workflows[0]["tools"])
        ]
    elif intent == "learning_plan":
        workflow_steps = [
            AgentWorkflowStep(
                order=index + 1,
                name=card["title"],
                objective=f"学习 {card['title']}，掌握该节点的核心概念和站内资料。",
                targetHref=card["href"],
                citationIds=[f"learning_node:{card['sourceKey']}"],
            )
            for index, card in enumerate(learning_cards)
        ]

    if page_cards and intent == "navigation":
        names = "、".join(card["title"] for card in page_cards[:5])
        answer = f"可以从这些站内页面继续：{names}。"
    elif learning_cards and intent in {"qa", "learning_plan"}:
        summaries = "；".join(f"{card['title']}：{card['description']}" for card in learning_cards[:3])
        answer = f"我根据站内学习内容整理了这些入口：{summaries}"
    elif tool_cards:
        names = "、".join(card["title"] for card in tool_cards[:5])
        answer = f"我根据站内工具目录找到了：{names}。推荐结果来自当前 Tools 事实库。"
    else:
        answer = "暂时没有找到足够相关的站内内容。可以换成学习主题、工具名称或具体任务再试。"
    response = AgentStructuredResponse(
        answer=answer,
        intent=intent,
        cards=cards,
        citations=citations,
        toolCalls=[
            AgentToolCall(
                name="learning.search",
                status="completed" if "learning.search" in capabilities else "skipped",
                resultCount=len(learning_cards),
            ),
            AgentToolCall(
                name="tools.search",
                status="completed" if "tools.search" in capabilities else "skipped",
                resultCount=len(tool_cards),
            ),
            AgentToolCall(
                name="tools.workflow",
                status="completed" if "tools.workflow" in capabilities else "skipped",
                resultCount=len(workflows),
            ),
            AgentToolCall(
                name="users.context",
                status="completed" if user_context else "skipped",
                resultCount=1 if user_context else 0,
            ),
            *(
                [AgentToolCall(name="navigation.read", resultCount=len(page_cards))]
                if "navigation.read" in capabilities
                else []
            ),
        ],
        workflowSteps=workflow_steps,
        workflowDraft=(
            AgentWorkflowDraft(
                title=workflows[0]["title"],
                description=workflows[0]["description"],
                sourceRef=workflows[0]["code"],
                steps=[
                    AgentWorkflowDraftStep(
                        order=step.order,
                        name=step.name,
                        objective=step.objective,
                        toolSlug=step.toolSlugs[0] if step.toolSlugs else None,
                    )
                    for step in workflow_steps
                ],
            )
            if workflows
            else None
        ),
        followups=[
            question
            for enabled, question in (
                (preferences.get("cnFirst"), "是否优先推荐国内可访问资源？"),
                (preferences.get("freeFirst"), "是否需要免费工具优先？"),
            )
            if not enabled
        ],
        meta=AgentResponseMeta(
            userContext=(
                AgentUserContextMeta(
                    source=user_context["meta"]["source"],
                    contractVersion=user_context["meta"]["contractVersion"],
                    assets=user_context.get("assets", {}),
                    capabilities=user_context.get("capabilities", {}),
                )
                if user_context
                else None
            )
        ),
    )
    return validate_response(response)
