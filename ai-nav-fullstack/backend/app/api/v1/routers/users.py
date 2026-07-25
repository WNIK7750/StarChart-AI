from typing import Callable, Literal, TypeVar

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import Field

from app.api.v1.routers.auth import get_current_user
from app.core.config import AVATAR_MAX_UPLOAD_BYTES, REFRESH_COOKIE_NAME
from app.core.security import hash_token
from app.users.account.service import get_account_service
from app.users.audit.service import get_audit_service
from app.users.assets.schemas import WorkflowListResponse
from app.users.assets.service import get_assets_service
from app.users.common import StrictModel, UsersError, users_error_detail
from app.users.preferences.service import get_preferences_service
from app.users.preferences.facade import get_user_preferences_facade
from app.users.profile.service import get_profile_service
from app.users.security.service import get_security_service
from app.users.sessions.service import get_sessions_service
from app.users.response_schemas import (
    AccountResponse,
    AccountUpdateResponse,
    AvatarUploadResponse,
    PreferenceContextResponse,
    PreferencesResponse,
    ProfileResponse,
    RevokeOtherSessionsResponse,
    SecurityQuestionsResponse,
    SessionListResponse,
    StatusMessageResponse,
    StatusResponse,
)

router = APIRouter(prefix="/users", tags=["users"])
T = TypeVar("T")

class AccountUpdate(StrictModel):
    username: str | None = Field(default=None, min_length=3, max_length=32)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=24)
    currentPassword: str | None = Field(default=None, min_length=8, max_length=128)


class PasswordUpdate(StrictModel):
    currentPassword: str = Field(min_length=8, max_length=128)
    newPassword: str = Field(min_length=8, max_length=128)


class ProfileUpdate(StrictModel):
    expectedVersion: int = Field(ge=1)
    displayName: str | None = Field(default=None, min_length=1, max_length=40)
    bio: str | None = Field(default=None, max_length=300)
    roleTitle: str | None = Field(default=None, max_length=60)
    learningLevel: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    targetDirection: str | None = Field(default=None, max_length=80)


class PreferencesUpdate(StrictModel):
    expectedVersion: int = Field(ge=1)
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
    language: str | None = Field(default=None, max_length=20)
    cnFirst: bool | None = None
    freeFirst: bool | None = None
    showExternalResources: bool | None = None


class SecurityQuestionItem(StrictModel):
    question: str = Field(min_length=2, max_length=80)
    answer: str = Field(min_length=2, max_length=80)


class SecurityQuestionsUpdate(StrictModel):
    currentPassword: str = Field(min_length=8, max_length=128)
    items: list[SecurityQuestionItem] = Field(min_length=1, max_length=3)


def _users_call(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except UsersError as exc:
        raise HTTPException(status_code=exc.status_code, detail=users_error_detail(exc)) from exc


def _refresh_hash_from_cookie(refresh_cookie: str | None) -> str | None:
    return hash_token(refresh_cookie) if refresh_cookie else None


def _audited_call(
    fn: Callable[[], T],
    *,
    event: str,
    current_user: dict,
    request: Request,
    resource_id: str,
    metadata: dict | Callable[[T], dict] | None = None,
) -> T:
    result = _users_call(fn)
    audit_metadata = metadata(result) if callable(metadata) else metadata
    get_audit_service().record(
        event,
        actor_user_id=current_user["id"],
        target_user_id=current_user["id"],
        resource_id=resource_id,
        metadata=audit_metadata,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    return result


@router.get("/me/account", response_model=AccountResponse)
def get_account(current_user: dict = Depends(get_current_user)):
    return _users_call(lambda: get_account_service().get_account(current_user["id"]))


@router.patch("/me/account", response_model=AccountUpdateResponse)
def update_account(payload: AccountUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    return _audited_call(
        lambda: get_account_service().update_account(
            current_user["id"],
            payload.model_dump(exclude_unset=True),
        ),
        event="users.account.updated",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata=lambda result: {"changedFields": result["meta"]["changedFields"]},
    )


@router.patch("/me/password", response_model=StatusMessageResponse)
def update_password(payload: PasswordUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    return _audited_call(
        lambda: get_security_service().update_password(
            current_user["id"],
            payload.currentPassword,
            payload.newPassword,
        ),
        event="users.security.password_updated",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata={"sessionsRevoked": True},
    )


@router.get("/me/security-questions", response_model=SecurityQuestionsResponse)
def get_security_questions(current_user: dict = Depends(get_current_user)):
    return get_security_service().list_security_questions(current_user["id"])


@router.put("/me/security-questions", response_model=SecurityQuestionsResponse)
def update_security_questions(payload: SecurityQuestionsUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    return _audited_call(
        lambda: get_security_service().replace_security_questions(
            current_user["id"],
            payload.currentPassword,
            [item.model_dump() for item in payload.items],
        ),
        event="users.security.questions_replaced",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata={"questionCount": len(payload.items)},
    )


@router.get("/me/profile", response_model=ProfileResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return _users_call(lambda: get_profile_service().get_profile(current_user["id"]))


@router.patch("/me/profile", response_model=ProfileResponse)
def update_profile(payload: ProfileUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    values = payload.model_dump(exclude={"expectedVersion"})
    return _audited_call(
        lambda: get_profile_service().update_profile(current_user["id"], values, payload.expectedVersion),
        event="users.profile.updated",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata={"changedFields": sorted(key for key, value in values.items() if value is not None)},
    )


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(request: Request, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    content = await file.read(AVATAR_MAX_UPLOAD_BYTES + 1)
    if len(content) > AVATAR_MAX_UPLOAD_BYTES:
        error = UsersError("AVATAR_TOO_LARGE", "头像原图超过大小限制", 413)
        raise HTTPException(status_code=error.status_code, detail=users_error_detail(error))
    return _audited_call(
        lambda: get_profile_service().upload_avatar(current_user["id"], content, file.content_type),
        event="users.profile.avatar_updated",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata=lambda result: {
            "format": result["meta"]["format"],
            "storedBytes": result["meta"]["storedBytes"],
            "oldAvatarRemoved": result["meta"]["oldAvatarRemoved"],
        },
    )


@router.get("/me/preferences", response_model=PreferencesResponse)
def get_preferences(current_user: dict = Depends(get_current_user)):
    return _users_call(lambda: get_preferences_service().get_preferences(current_user["id"]))


@router.get("/me/preferences/context", response_model=PreferenceContextResponse)
def get_preference_context(
    consumer: Literal["learning", "tools", "agent"] = Query(...),
    current_user: dict = Depends(get_current_user),
):
    return _users_call(
        lambda: get_user_preferences_facade().get_context(current_user["id"], consumer)
    )


@router.patch("/me/preferences", response_model=PreferencesResponse)
def update_preferences(payload: PreferencesUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    values = payload.model_dump(exclude={"expectedVersion"})
    return _audited_call(
        lambda: get_preferences_service().update_preferences(current_user["id"], values, payload.expectedVersion),
        event="users.preferences.updated",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata={"changedFields": sorted(key for key, value in values.items() if value is not None)},
    )


@router.get("/me/sessions", response_model=SessionListResponse)
def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    current_user: dict = Depends(get_current_user),
):
    return get_sessions_service().list_sessions(current_user["id"], page, page_size, _refresh_hash_from_cookie(refresh_cookie))


@router.post("/me/sessions/revoke-others", response_model=RevokeOtherSessionsResponse)
def revoke_other_sessions(
    request: Request,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    current_user: dict = Depends(get_current_user),
):
    return _audited_call(
        lambda: get_sessions_service().revoke_other_sessions(
            current_user["id"], _refresh_hash_from_cookie(refresh_cookie)
        ),
        event="users.sessions.others_revoked",
        current_user=current_user,
        request=request,
        resource_id=current_user["user_uid"],
        metadata=lambda result: {"scope": "others", "revokedCount": result["revokedCount"]},
    )


@router.delete("/me/sessions/{session_uid}", response_model=StatusResponse)
def revoke_session(session_uid: str, request: Request, current_user: dict = Depends(get_current_user)):
    return _audited_call(
        lambda: get_sessions_service().revoke_session(current_user["id"], session_uid),
        event="users.session.revoked",
        current_user=current_user,
        request=request,
        resource_id=session_uid,
        metadata={"scope": "single"},
    )


@router.get("/me/workflows", response_model=WorkflowListResponse)
def saved_workflows(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    return _users_call(
        lambda: get_assets_service().list_workflows(current_user["id"], page, page_size, "active")
    )
