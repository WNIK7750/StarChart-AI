from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query

from app.api.v1.dependencies.authorization import require_permission
from app.api.v1.routers.auth import get_current_user
from app.api.v1.schemas import ErrorResponse
from app.users.learning_state import (
    LearningStateConflictError,
    LearningStateNotFoundError,
    LearningStateValidationError,
    get_user_learning_state_service,
)
from app.users.learning_state.schemas import (
    ActivityCreate,
    ActivityResponse,
    DashboardResponse,
    FavoriteCreate,
    FavoriteResponse,
    FavoritesResponse,
    ProgressListResponse,
    ProgressResponse,
    ProgressUpdate,
    RecentResponse,
    ResumeResponse,
    NodeLearningStateResponse,
    SectionProgressResponse,
    SectionProgressUpdate,
    AnonymousLearningImport,
    AnonymousLearningImportResult,
)

router = APIRouter(
    prefix="/users/me",
    tags=["user-learning"],
    dependencies=[Depends(require_permission("learning:read"))],
)


def _service_error(exc: Exception):
    if isinstance(exc, LearningStateConflictError):
        raise HTTPException(status_code=409, detail={"code": exc.code, "message": str(exc)}) from exc
    if isinstance(exc, LearningStateValidationError):
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc
    raise HTTPException(status_code=404, detail={"code": getattr(exc, "code", "LEARNING_TARGET_NOT_FOUND"), "message": str(exc)}) from exc


@router.get("/learning/dashboard", response_model=DashboardResponse)
def learning_dashboard(current_user: dict = Depends(get_current_user)):
    return get_user_learning_state_service().dashboard(current_user["id"])


@router.get("/learning/progress", response_model=ProgressListResponse)
def learning_progress(current_user: dict = Depends(get_current_user)):
    return get_user_learning_state_service().list_progress(current_user["id"])


@router.get("/learning/nodes/{node_slug}", response_model=NodeLearningStateResponse, responses={404: {"model": ErrorResponse}})
def learning_node_state(
    node_slug: str = Path(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$"),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_user_learning_state_service().node_state(current_user["id"], node_slug)
    except LearningStateNotFoundError as exc:
        _service_error(exc)


@router.put(
    "/learning/nodes/{node_slug}/sections/{section_uid}",
    response_model=SectionProgressResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_learning_section_progress(
    payload: SectionProgressUpdate,
    node_slug: str = Path(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$"),
    section_uid: str = Path(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_user_learning_state_service().set_section_progress(
            current_user["id"], node_slug, section_uid, payload.isCompleted, payload.expectedVersion
        )
    except (LearningStateNotFoundError, LearningStateConflictError) as exc:
        _service_error(exc)


@router.put("/learning/progress/{node_slug}", response_model=ProgressResponse, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def update_learning_progress(
    payload: ProgressUpdate,
    node_slug: str = Path(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$"),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_user_learning_state_service().set_progress(current_user["id"], node_slug, payload.progressPercent, payload.status, payload.expectedVersion)
    except (LearningStateNotFoundError, LearningStateConflictError, LearningStateValidationError) as exc:
        _service_error(exc)


@router.post("/learning/activity", status_code=201, response_model=ActivityResponse, responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def create_learning_activity(
    payload: ActivityCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_user_learning_state_service().record_activity(current_user["id"], {**payload.model_dump(), "idempotencyKey": idempotency_key})
    except (LearningStateNotFoundError, LearningStateValidationError) as exc:
        _service_error(exc)


@router.post(
    "/learning/import",
    response_model=AnonymousLearningImportResult,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def import_anonymous_learning_state(
    payload: AnonymousLearningImport,
    current_user: dict = Depends(get_current_user),
):
    try:
        return get_user_learning_state_service().import_anonymous_state(
            current_user["id"], payload.snapshotId, [item.model_dump() for item in payload.nodeViews]
        )
    except (LearningStateNotFoundError, LearningStateValidationError) as exc:
        _service_error(exc)


@router.get("/learning/recent", response_model=RecentResponse)
def recent_learning(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    return get_user_learning_state_service().recent(current_user["id"], page, page_size)


@router.get("/learning/resume", response_model=ResumeResponse)
def resume_learning(current_user: dict = Depends(get_current_user)):
    return get_user_learning_state_service().resume(current_user["id"])


@router.get("/favorites", response_model=FavoritesResponse)
def list_favorites(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    return get_user_learning_state_service().list_favorites(current_user["id"], page, page_size)


@router.post("/favorites", status_code=201, response_model=FavoriteResponse, responses={404: {"model": ErrorResponse}})
def add_favorite(payload: FavoriteCreate, current_user: dict = Depends(get_current_user)):
    try:
        return get_user_learning_state_service().add_favorite(current_user["id"], payload.targetType, payload.targetKey)
    except LearningStateNotFoundError as exc:
        _service_error(exc)


@router.delete("/favorites/{favorite_uid}", status_code=204, responses={404: {"model": ErrorResponse}})
def remove_favorite(
    favorite_uid: str = Path(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"),
    current_user: dict = Depends(get_current_user),
):
    try:
        get_user_learning_state_service().remove_favorite(current_user["id"], favorite_uid)
    except LearningStateNotFoundError as exc:
        _service_error(exc)
