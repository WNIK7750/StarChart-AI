from ipaddress import ip_address, ip_network

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import Field

from app.api.v1.dependencies.deployment_policy import require_deployment_action
from app.api.v1.schemas import ErrorResponse
from app.core.config import (
    REFRESH_COOKIE_MAX_AGE_SECONDS,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_COOKIE_SAMESITE,
    REFRESH_COOKIE_SECURE,
    TRUSTED_PROXY_CIDRS,
)
from app.users.account.service import get_account_service, normalize_username as normalize_username_policy
from app.users.authentication.service import RequestContext, get_authentication_service, normalize_email as normalize_email_policy
from app.users.authentication.schemas import (
    AccessTokenResponse,
    AuthResponse,
    StatusMessageResponse,
    StatusResponse,
    UsernameAvailableResponse,
    UserResponse,
)
from app.users.authentication.rate_limit import get_auth_rate_limiter
from app.users.common import StrictModel, UsersError, users_error_detail
from app.users.security.service import hash_security_answer as hash_security_answer_policy
from app.users.security.service import validate_password_strength as validate_password_strength_policy

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(StrictModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=24)
    displayName: str | None = Field(default=None, max_length=40)
    privacyAccepted: bool


class LoginRequest(StrictModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    deviceName: str | None = Field(default=None, max_length=80)
    privacyAccepted: bool
    rememberMe: bool = False


class RefreshRequest(StrictModel):
    refreshToken: str | None = Field(default=None, min_length=20)


class PasswordResetStartRequest(StrictModel):
    identifier: str = Field(min_length=3, max_length=254)


class PasswordResetVerifyRequest(StrictModel):
    resetUid: str = Field(min_length=8, max_length=80)
    answers: list[str] = Field(min_length=1, max_length=3)


class PasswordResetConfirmRequest(StrictModel):
    resetToken: str = Field(min_length=20, max_length=160)
    newPassword: str = Field(min_length=8, max_length=128)


def _client_ip(request: Request, trusted_proxy_cidrs: tuple[str, ...] = TRUSTED_PROXY_CIDRS) -> str:
    direct = request.client.host if request.client else ""
    try:
        direct_ip = ip_address(direct)
        trusted_networks = tuple(ip_network(value, strict=False) for value in trusted_proxy_cidrs)
    except ValueError:
        return direct
    if not any(direct_ip in network for network in trusted_networks):
        return direct
    forwarded = [value.strip() for value in request.headers.get("x-forwarded-for", "").split(",") if value.strip()]
    try:
        forwarded_ips = [ip_address(value) for value in forwarded]
    except ValueError:
        return direct
    for candidate in reversed(forwarded_ips):
        if not any(candidate in network for network in trusted_networks):
            return str(candidate)
    return str(forwarded_ips[0]) if forwarded_ips else direct


def _context(request: Request) -> RequestContext:
    return RequestContext(ip_address=_client_ip(request), user_agent=request.headers.get("user-agent", ""))


def _auth_call(fn):
    try:
        return fn()
    except UsersError as exc:
        raise HTTPException(status_code=exc.status_code, detail=users_error_detail(exc)) from exc


def _enforce_rate_limit(operation: str, subjects: dict[str, str]) -> None:
    try:
        get_auth_rate_limiter().enforce(operation, subjects)
    except UsersError as exc:
        headers = {"Retry-After": str(getattr(exc, "retry_after", 1))}
        raise HTTPException(status_code=exc.status_code, detail=users_error_detail(exc), headers=headers) from exc


def _set_refresh_cookie(response: Response, refresh_token: str | None, persistent: bool = True) -> None:
    if not refresh_token:
        return
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE_SECONDS if persistent else None,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=REFRESH_COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
    )


def _without_refresh_token(result: dict) -> dict:
    return {key: value for key, value in result.items() if key != "refreshToken"}


def _refresh_token_from(payload: RefreshRequest | None, cookie_token: str | None) -> str:
    token = cookie_token or (payload.refreshToken if payload else None)
    if not token:
        raise UsersError("REFRESH_TOKEN_REQUIRED", "缺少刷新令牌", 401)
    return token


def normalize_email(email: str | None) -> str | None:
    return _auth_call(lambda: normalize_email_policy(email))


def normalize_username(username: str) -> str:
    return _auth_call(lambda: normalize_username_policy(username))


def validate_password_strength(password: str) -> str:
    return _auth_call(lambda: validate_password_strength_policy(password))


def hash_security_answer(answer: str) -> str:
    return _auth_call(lambda: hash_security_answer_policy(answer))


def ensure_username_available(cur, username: str, exclude_user_id: int | None = None) -> None:
    del cur
    available = get_account_service().repository.is_username_available(username, exclude_user_id)
    if not available:
        raise HTTPException(status_code=409, detail=users_error_detail(UsersError("USERNAME_TAKEN", "用户名已被使用", 409)))


def _public_user(row: dict) -> dict:
    return {
        "userUid": row["user_uid"],
        "username": row["username"],
        "email": row["email"],
        "phone": row["phone"],
        "accountStatus": row["account_status"],
        "emailVerified": bool(row["email_verified"]),
        "phoneVerified": bool(row["phone_verified"]),
        "lastLoginAt": row["last_login_at"],
        "createdAt": row["created_at"],
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=users_error_detail(UsersError("AUTH_REQUIRED", "未登录", 401)),
        )
    token = authorization.split(" ", 1)[1].strip()
    return _auth_call(lambda: get_authentication_service().current_user_from_token(token))


@router.get(
    "/username-available",
    response_model=UsernameAvailableResponse,
    dependencies=[Depends(require_deployment_action("register"))],
)
def username_available(request: Request, username: str = Query(min_length=3, max_length=32)):
    _enforce_rate_limit("username_available", {"ip": _client_ip(request)})
    return _auth_call(lambda: get_authentication_service().username_available(username))


@router.post(
    "/register",
    status_code=201,
    response_model=AuthResponse,
    dependencies=[Depends(require_deployment_action("register"))],
)
def register(payload: RegisterRequest, request: Request, response: Response):
    _enforce_rate_limit("register", {"ip": _client_ip(request)})
    result = _auth_call(lambda: get_authentication_service().register(payload.model_dump(), _context(request)))
    _set_refresh_cookie(response, result.get("refreshToken"), persistent=False)
    return _without_refresh_token(result)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(require_deployment_action("login"))],
)
def login(payload: LoginRequest, request: Request, response: Response):
    _enforce_rate_limit("login", {"ip": _client_ip(request), "identifier": payload.identifier})
    result = _auth_call(lambda: get_authentication_service().login(payload.model_dump(), _context(request)))
    _set_refresh_cookie(response, result.get("refreshToken"), persistent=payload.rememberMe)
    return _without_refresh_token(result)


def _password_reset_start(payload: PasswordResetStartRequest, request: Request):
    _enforce_rate_limit("password_reset_start", {"ip": _client_ip(request), "identifier": payload.identifier})
    return _auth_call(lambda: get_authentication_service().password_reset_start(payload.identifier, _context(request)))


@router.post(
    "/password-reset/start",
    response_model=StatusMessageResponse,
    dependencies=[Depends(require_deployment_action("recovery"))],
)
def password_reset_start(payload: PasswordResetStartRequest, request: Request):
    return _password_reset_start(payload, request)


@router.post(
    "/password-reset/security/start",
    deprecated=True,
    response_model=StatusMessageResponse,
    dependencies=[Depends(require_deployment_action("recovery"))],
)
def password_reset_security_start(payload: PasswordResetStartRequest, request: Request):
    return _password_reset_start(payload, request)


@router.post(
    "/password-reset/security/verify",
    deprecated=True,
    response_model=StatusMessageResponse,
    responses={410: {"model": ErrorResponse}},
    dependencies=[Depends(require_deployment_action("recovery"))],
)
def password_reset_security_verify(payload: PasswordResetVerifyRequest, request: Request):
    _enforce_rate_limit("password_reset_verify", {"ip": _client_ip(request), "challenge": payload.resetUid})
    return _auth_call(
        lambda: get_authentication_service().password_reset_security_verify(
            payload.resetUid,
            payload.answers,
            _context(request),
        )
    )


def _password_reset_confirm(payload: PasswordResetConfirmRequest, request: Request):
    _enforce_rate_limit("password_reset_confirm", {"ip": _client_ip(request), "token": payload.resetToken})
    return _auth_call(
        lambda: get_authentication_service().password_reset_confirm(
            payload.resetToken,
            payload.newPassword,
            _context(request),
        )
    )


@router.post(
    "/password-reset/confirm",
    response_model=StatusMessageResponse,
    dependencies=[Depends(require_deployment_action("recovery"))],
)
def password_reset_confirm(payload: PasswordResetConfirmRequest, request: Request):
    return _password_reset_confirm(payload, request)


@router.post(
    "/password-reset/security/confirm",
    deprecated=True,
    response_model=StatusMessageResponse,
    dependencies=[Depends(require_deployment_action("recovery"))],
)
def password_reset_security_confirm(payload: PasswordResetConfirmRequest, request: Request):
    return _password_reset_confirm(payload, request)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    _enforce_rate_limit("refresh", {"ip": _client_ip(request)})
    result, persistent = _auth_call(
        lambda: get_authentication_service().refresh_with_cookie_policy(
            _refresh_token_from(payload, refresh_cookie),
            _context(request),
        )
    )
    _set_refresh_cookie(response, result.get("refreshToken"), persistent=persistent)
    return _without_refresh_token(result)


@router.post("/logout", response_model=StatusResponse)
def logout(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    current_user: dict = Depends(get_current_user),
):
    result = _auth_call(
        lambda: get_authentication_service().logout(
            current_user["id"],
            _refresh_token_from(payload, refresh_cookie),
            user_uid=current_user["user_uid"],
            context=_context(request),
        )
    )
    _clear_refresh_cookie(response)
    return result


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return {"user": _public_user(current_user)}
