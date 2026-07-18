import re

from app.agent.evaluator import validate_response
from app.agent.router import classify_intent
from app.agent.schemas import (
    AgentChatRequest,
    AgentCitation,
    AgentLinkCard,
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
from app.tools.service import focus_task_query


def agent_retrieval_query(message: str) -> str:
    focused = focus_task_query(message)
    for token in ["怎么学", "如何学", "学习路线", "学习计划", "推荐", "工具", "帮我", "我要", "我想", "做"]:
        focused = focused.replace(token, " ")
    focused = re.sub(r"[，。！？；：、,.!?;:]+", " ", focused)
    return " ".join(focused.split()) or message.strip()


def draft_agent_response(request: AgentChatRequest, user_context: dict | None = None) -> AgentStructuredResponse:
    """Deterministic Agent foundation grounded in site data.

    This is not the final LLM orchestration layer. It deliberately keeps
    retrieval, link cards, workflow candidates, and response validation behind
    stable module boundaries so a later model call can be inserted without
    rewriting the tool catalog or API contracts.
    """
    intent = classify_intent(request.message)
    retrieval_query = agent_retrieval_query(request.message)
    tool_cards = search_tool_cards(retrieval_query, limit=5)
    learning_cards = search_learning_cards(retrieval_query, limit=5)
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
    workflows = suggest_workflow(retrieval_query, limit=1) if intent == "workflow_generation" else []

    ordered_cards = (
        [*tool_cards, *learning_cards]
        if intent in {"tool_recommendation", "workflow_generation"}
        else [*learning_cards, *tool_cards]
    )

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

    if learning_cards and intent in {"qa", "navigation", "learning_plan"}:
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
            AgentToolCall(name="learning.search", resultCount=len(learning_cards)),
            AgentToolCall(name="tools.search", resultCount=len(tool_cards)),
            AgentToolCall(
                name="tools.workflow",
                status="completed" if intent == "workflow_generation" else "skipped",
                resultCount=len(workflows),
            ),
            AgentToolCall(name="users.context", resultCount=1 if user_context else 0),
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
