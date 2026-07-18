from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.v1.dependencies.authorization import require_permission
from app.agent.schemas import AgentChatRequest, AgentErrorResponse, AgentStructuredResponse
from app.agent.service import draft_agent_response
from app.users.assets.facade import get_user_assets_facade
from app.users.assets.schemas import WorkflowCreate
from app.users.context.facade import get_user_context_facade

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/chat",
    response_model=AgentStructuredResponse,
    responses={401: {"model": AgentErrorResponse}, 403: {"model": AgentErrorResponse}},
)
def agent_chat(payload: AgentChatRequest, current_user: dict = Depends(require_permission("agent:chat"))):
    user_context = get_user_context_facade().for_agent(current_user["id"])
    return draft_agent_response(payload, user_context)


@router.post("/workflows/save", status_code=201)
def save_agent_workflow(
    payload: WorkflowCreate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    if payload.sourceType != "agent":
        raise HTTPException(
            status_code=422,
            detail={"code": "AGENT_WORKFLOW_SOURCE_INVALID", "message": "Agent 保存命令只接受 agent 来源"},
        )
    context = {
        "actorUserId": current_user["id"],
        "targetUserId": current_user["id"],
        "ipAddress": request.client.host if request.client else None,
        "userAgent": request.headers.get("User-Agent"),
    }
    return get_user_assets_facade().save_workflow(
        current_user["id"],
        payload.model_dump(),
        idempotency_key,
        context,
    )
