from fastapi import APIRouter, HTTPException, Path, Query

from app.api.v1.schemas import ErrorResponse
from app.learning import LearningNotFoundError, get_learning_service
from app.learning.schemas import (
    AgentLearningContextResponse,
    LearningNodeResponse,
    NodeRelationsResponse,
    LearningResourcesResponse,
    LearningSearchResponse,
    NextLearningNodeResponse,
    RoadmapResponse,
)

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/roadmap", response_model=RoadmapResponse)
def get_roadmap():
    return get_learning_service().get_roadmap()


@router.get("/resources", response_model=LearningResourcesResponse)
def get_learning_resources(domain: str | None = Query(default=None)):
    return get_learning_service().list_resources(domain)


@router.get("/search", response_model=LearningSearchResponse)
def search_learning(q: str = Query(default="", max_length=120), limit: int = Query(default=10, ge=1, le=30)):
    return get_learning_service().search(q, limit)


@router.get("/agent-context", response_model=AgentLearningContextResponse)
def get_agent_learning_context(q: str = Query(default="", max_length=120), limit: int = Query(default=7, ge=1, le=20)):
    return get_learning_service().get_agent_context(q, limit)


@router.get("/nodes/{slug}/next", response_model=NextLearningNodeResponse)
def get_next_learning_node(slug: str = Path(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")):
    return {"item": get_learning_service().recommend_next(slug), "meta": {"contractVersion": 1}}


@router.get("/nodes/{slug}/relations", response_model=NodeRelationsResponse, responses={404: {"model": ErrorResponse}})
def get_learning_node_relations(slug: str = Path(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")):
    try:
        return get_learning_service().get_relations(slug)
    except LearningNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/nodes/{slug}", response_model=LearningNodeResponse, responses={404: {"model": ErrorResponse}})
def get_learning_node(slug: str = Path(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")):
    try:
        return get_learning_service().get_node(slug)
    except LearningNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": str(exc)}) from exc
