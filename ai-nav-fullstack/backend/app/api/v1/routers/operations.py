from fastapi import APIRouter, Depends

from app.api.v1.dependencies.authorization import require_permission
from app.users.observability.metrics import get_users_metrics
from app.users.response_schemas import UsersMetricsResponse


router = APIRouter(prefix="/users/operations", tags=["user-operations"])


@router.get("/metrics", response_model=UsersMetricsResponse)
def users_metrics(_: dict = Depends(require_permission("users:manage"))):
    return get_users_metrics().snapshot()
