from app.agent.evaluator import validate_response
from app.agent.router import classify_intent
from app.agent.schemas import AgentChatRequest, AgentLinkCard, AgentStructuredResponse, AgentWorkflowStep
from app.agent.tools.catalog_tools import search_tool_cards, suggest_workflow
from app.services.tool_catalog import focus_task_query


def draft_agent_response(request: AgentChatRequest) -> AgentStructuredResponse:
    """Deterministic Agent foundation grounded in site data.

    This is not the final LLM orchestration layer. It deliberately keeps
    retrieval, link cards, workflow candidates, and response validation behind
    stable module boundaries so a later model call can be inserted without
    rewriting the tool catalog or API contracts.
    """
    intent = classify_intent(request.message)
    retrieval_query = focus_task_query(request.message)
    tool_cards = search_tool_cards(retrieval_query, limit=5)
    workflows = suggest_workflow(request.message, limit=1)

    cards = [
        AgentLinkCard(
            type=card["type"],
            title=card["title"],
            description=card["description"],
            href=card["href"],
        )
        for card in tool_cards
    ]

    workflow_steps: list[AgentWorkflowStep] = []
    if workflows:
        workflow_steps = [
            AgentWorkflowStep(
                order=index + 1,
                name=tool["name"],
                objective=f"用于{workflows[0]['title']}中的第 {index + 1} 步。",
                toolSlugs=[tool["id"]],
            )
            for index, tool in enumerate(workflows[0]["tools"])
        ]

    answer = (
        "我先根据站内工具库找到了这些相关工具。后续接入模型后，会在这个检索结果之上生成更细的解释、跳转和专属工作流。"
        if cards
        else "暂时没有在站内工具库找到足够相关的工具。你可以换成工具名、用途或场景词再试。"
    )
    response = AgentStructuredResponse(
        answer=answer,
        intent=intent,
        cards=cards,
        workflowSteps=workflow_steps,
        followups=["是否优先推荐国内可访问资源？", "是否需要免费工具优先？"],
    )
    return validate_response(response)
