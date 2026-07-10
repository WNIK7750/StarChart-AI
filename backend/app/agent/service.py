from app.agent.evaluator import validate_response
from app.agent.router import classify_intent
from app.agent.schemas import AgentChatRequest, AgentStructuredResponse


def draft_agent_response(request: AgentChatRequest) -> AgentStructuredResponse:
    """Minimal deterministic fallback for the future Agent service.

    The real LLM orchestration should plug in here, after retrieving site data
    through dedicated tools. Keeping this shape now makes the later Agent
    rewrite smaller and safer.
    """
    intent = classify_intent(request.message)
    response = AgentStructuredResponse(
        answer="Agent 服务接口位置已预留。后续会在这里接入检索、工具选择、链接校验和工作流生成。",
        intent=intent,
        followups=["是否优先推荐国内可访问资源？", "是否需要免费工具优先？"],
    )
    return validate_response(response)
