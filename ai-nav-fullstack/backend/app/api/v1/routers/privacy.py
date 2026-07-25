from collections.abc import Callable
from typing import Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from app.api.v1.dependencies.authorization import require_permission
from app.api.v1.routers.auth import get_current_user
from app.users.audit.service import get_audit_service
from app.users.common import StrictModel, UsersError, users_error_detail
from app.users.privacy.service import get_privacy_service
from app.users.response_schemas import (
    ConsentResponse,
    ConsentStatusResponse,
    DataExportResponse,
    DataRequestResponse,
    DeletionAdminResponse,
    DeletionAnonymizeResponse,
)


router = APIRouter(tags=["privacy"])
T = TypeVar("T")


class ConsentUpdate(StrictModel):
    policyVersion: str = Field(min_length=1, max_length=40)
    granted: bool


class DataExportRequest(StrictModel):
    currentPassword: str = Field(min_length=8, max_length=128)


class DeletionRequestCreate(StrictModel):
    currentPassword: str = Field(min_length=8, max_length=128)
    reasonCode: Literal["privacy", "unused", "other"]


def _privacy_call(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except UsersError as exc:
        raise HTTPException(status_code=exc.status_code, detail=users_error_detail(exc)) from exc


def _record(
    event: str,
    *,
    actor: dict,
    target_user_id: int,
    resource_id: str,
    request: Request,
    metadata: dict | None = None,
) -> None:
    get_audit_service().record(
        event,
        actor_user_id=actor["id"],
        target_user_id=target_user_id,
        resource_id=resource_id,
        metadata=metadata,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )


@router.get("/users/me/privacy/consents", response_model=ConsentStatusResponse)
def consent_status(current_user: dict = Depends(get_current_user)):
    return get_privacy_service().consent_status(current_user["id"])


@router.put("/users/me/privacy/consents/{consent_type}", response_model=ConsentResponse)
def update_consent(
    consent_type: Literal["privacy_policy", "agent_memory"],
    payload: ConsentUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    result = _privacy_call(
        lambda: get_privacy_service().set_consent(
            current_user["id"],
            consent_type,
            payload.policyVersion,
            payload.granted,
        )
    )
    _record(
        "users.privacy.consent_updated",
        actor=current_user,
        target_user_id=current_user["id"],
        resource_id=consent_type,
        request=request,
        metadata={
            "consentType": consent_type,
            "policyVersion": payload.policyVersion,
            "status": result["consent"]["status"],
        },
    )
    return result


@router.post("/users/me/privacy/export", response_model=DataExportResponse)
def export_data(
    payload: DataExportRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    result = _privacy_call(
        lambda: get_privacy_service().export_user_data(current_user["id"], payload.currentPassword)
    )
    _record(
        "users.privacy.data_exported",
        actor=current_user,
        target_user_id=current_user["id"],
        resource_id=result["request"]["requestUid"],
        request=request,
        metadata={"formatVersion": result["export"]["formatVersion"]},
    )
    return result


@router.get("/users/me/privacy/deletion-requests/current", response_model=DataRequestResponse)
def current_deletion_request(current_user: dict = Depends(get_current_user)):
    return get_privacy_service().current_deletion_request(current_user["id"])


@router.post("/users/me/privacy/deletion-requests", status_code=201, response_model=DataRequestResponse)
def request_deletion(
    payload: DeletionRequestCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    result = _privacy_call(
        lambda: get_privacy_service().request_deletion(
            current_user["id"],
            payload.currentPassword,
            payload.reasonCode,
        )
    )
    _record(
        "users.privacy.deletion_requested",
        actor=current_user,
        target_user_id=current_user["id"],
        resource_id=result["request"]["requestUid"],
        request=request,
        metadata={
            "reasonCode": payload.reasonCode,
            "scheduledFor": result["request"]["scheduledFor"],
        },
    )
    return result


@router.delete("/users/me/privacy/deletion-requests/{request_uid}", response_model=DataRequestResponse)
def cancel_deletion(
    request_uid: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    result = _privacy_call(
        lambda: get_privacy_service().cancel_deletion(current_user["id"], request_uid)
    )
    _record(
        "users.privacy.deletion_cancelled",
        actor=current_user,
        target_user_id=current_user["id"],
        resource_id=request_uid,
        request=request,
    )
    return result


@router.post("/users/privacy/deletion-requests/{request_uid}/execute", response_model=DeletionAdminResponse)
def execute_deletion(
    request_uid: str,
    request: Request,
    current_user: dict = Depends(require_permission("users:manage")),
):
    result = _privacy_call(lambda: get_privacy_service().execute_deletion(request_uid))
    _record(
        "users.privacy.deletion_executed",
        actor=current_user,
        target_user_id=result["userId"],
        resource_id=request_uid,
        request=request,
        metadata={"retentionUntil": result["request"]["retentionUntil"]},
    )
    return result


@router.post("/users/privacy/deletion-requests/{request_uid}/restore", response_model=DeletionAdminResponse)
def restore_deletion(
    request_uid: str,
    request: Request,
    current_user: dict = Depends(require_permission("users:manage")),
):
    result = _privacy_call(lambda: get_privacy_service().restore_deletion(request_uid))
    _record(
        "users.privacy.deletion_restored",
        actor=current_user,
        target_user_id=result["userId"],
        resource_id=request_uid,
        request=request,
    )
    return result


@router.post("/users/privacy/deletion-requests/{request_uid}/anonymize", response_model=DeletionAnonymizeResponse)
def anonymize_deletion(
    request_uid: str,
    request: Request,
    current_user: dict = Depends(require_permission("users:manage")),
):
    result = _privacy_call(lambda: get_privacy_service().anonymize_deletion(request_uid))
    _record(
        "users.privacy.deletion_anonymized",
        actor=current_user,
        target_user_id=result["userId"],
        resource_id=request_uid,
        request=request,
    )
    return result
