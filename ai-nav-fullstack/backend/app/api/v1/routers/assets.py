from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.api.v1.routers.auth import get_current_user
from app.users.assets.schemas import (
    WorkflowCreate,
    WorkflowCreateResponse,
    WorkflowEnvelope,
    WorkflowListResponse,
    WorkflowStatusUpdate,
    WorkflowUpdate,
)
from app.users.assets.service import get_assets_service
from app.users.common import UsersError, users_error_detail


router = APIRouter(prefix="/users/me/assets", tags=["user-assets"])


def _call(fn):
    try:
        return fn()
    except UsersError as exc:
        raise HTTPException(status_code=exc.status_code, detail=users_error_detail(exc)) from exc


def _context(user: dict, request: Request) -> dict:
    return {
        "actorUserId": user["id"],
        "targetUserId": user["id"],
        "ipAddress": request.client.host if request.client else None,
        "userAgent": request.headers.get("User-Agent"),
    }


@router.get("/workflows", response_model=WorkflowListResponse)
def list_workflows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    status: Literal["active", "archived", "all"] = "active",
    current_user: dict = Depends(get_current_user),
):
    return _call(lambda: get_assets_service().list_workflows(current_user["id"], page, page_size, status))


@router.post("/workflows", status_code=201, response_model=WorkflowCreateResponse)
def create_workflow(
    payload: WorkflowCreate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    current_user: dict = Depends(get_current_user),
):
    return _call(
        lambda: get_assets_service().create_workflow(
            current_user["id"],
            payload.model_dump(),
            idempotency_key,
            _context(current_user, request),
        )
    )


@router.get("/workflows/{workflow_uid}", response_model=WorkflowEnvelope)
def get_workflow(workflow_uid: str, current_user: dict = Depends(get_current_user)):
    return _call(lambda: get_assets_service().get_workflow(current_user["id"], workflow_uid))


@router.patch("/workflows/{workflow_uid}", response_model=WorkflowEnvelope)
def update_workflow(
    workflow_uid: str,
    payload: WorkflowUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return _call(
        lambda: get_assets_service().update_workflow(
            current_user["id"],
            workflow_uid,
            payload.expectedVersion,
            payload.model_dump(exclude={"expectedVersion"}),
            _context(current_user, request),
        )
    )


@router.post("/workflows/{workflow_uid}/archive", response_model=WorkflowEnvelope)
def archive_workflow(
    workflow_uid: str,
    payload: WorkflowStatusUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return _call(
        lambda: get_assets_service().set_status(
            current_user["id"], workflow_uid, payload.expectedVersion, "archived", _context(current_user, request)
        )
    )


@router.post("/workflows/{workflow_uid}/restore", response_model=WorkflowEnvelope)
def restore_workflow(
    workflow_uid: str,
    payload: WorkflowStatusUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return _call(
        lambda: get_assets_service().set_status(
            current_user["id"], workflow_uid, payload.expectedVersion, "active", _context(current_user, request)
        )
    )
