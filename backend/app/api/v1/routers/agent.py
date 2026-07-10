from fastapi import APIRouter, Depends

from app.agent.schemas import AgentChatRequest
from app.agent.service import draft_agent_response
from app.api.v1.routers.auth import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
def agent_chat(payload: AgentChatRequest, current_user: dict = Depends(get_current_user)):
    response = draft_agent_response(payload)
    return {
        **response.model_dump(),
        "meta": {
            "userUid": current_user["user_uid"],
            "source": "reserved",
            "message": "Agent 模块化接口已预留，后续接入检索、工具调用和工作流生成。",
        },
    }
