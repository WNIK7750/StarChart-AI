import re
import sqlite3
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    iso_datetime,
    random_uid,
    utc_now,
    verify_password,
)
from app.db.database import db_cursor

router = APIRouter(prefix="/auth", tags=["auth"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RESERVED_USERNAMES = {
    "admin",
    "administrator",
    "root",
    "system",
    "support",
    "official",
    "moderator",
    "null",
    "undefined",
    "api",
    "agent",
    "ai-nav",
    "ainav",
}
SENSITIVE_USERNAME_WORDS = {
    "管理员",
    "官方",
    "客服",
    "系统",
    "平台",
    "运营",
    "审核",
    "root",
    "admin",
}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    displayName: str | None = Field(default=None, max_length=40)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    deviceName: str | None = Field(default=None, max_length=80)


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=20)


class PasswordResetStartRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)


class PasswordResetVerifyRequest(BaseModel):
    resetUid: str = Field(min_length=8, max_length=80)
    answers: list[str] = Field(min_length=1, max_length=3)


class PasswordResetConfirmRequest(BaseModel):
    resetToken: str = Field(min_length=20, max_length=160)
    newPassword: str = Field(min_length=8, max_length=128)

    @field_validator("newPassword")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else ""


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    value = email.strip().lower()
    if not EMAIL_RE.match(value):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    return value


def normalize_username(username: str) -> str:
    value = username.strip()
    if not USERNAME_RE.match(value):
        raise HTTPException(status_code=422, detail="用户名只能包含中文、字母、数字、下划线和短横线，长度为 3-32 位")
    lower_value = value.lower()
    if lower_value in RESERVED_USERNAMES:
        raise HTTPException(status_code=422, detail="该用户名为系统保留名称")
    if any(word in lower_value or word in value for word in SENSITIVE_USERNAME_WORDS):
        raise HTTPException(status_code=422, detail="用户名包含不适合使用的词")
    return value


def validate_password_strength(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise ValueError("密码长度必须为 8-128 位")
    checks = [
        any(ch.islower() for ch in password),
        any(ch.isupper() for ch in password),
        any(ch.isdigit() for ch in password),
    ]
    if sum(checks) < 2:
        raise ValueError("密码至少需要包含大写字母、小写字母、数字中的两类")
    common = {"password", "12345678", "qwerty123", "admin123", "letmein"}
    if password.lower() in common:
        raise ValueError("密码过于常见，请换一个更安全的密码")
    return password


def normalize_security_answer(answer: str) -> str:
    value = " ".join(answer.strip().lower().split())
    if len(value) < 2 or len(value) > 80:
        raise HTTPException(status_code=422, detail="密保答案长度必须为 2-80 位")
    return value


def hash_security_answer(answer: str) -> str:
    return hash_token(f"security-answer:{normalize_security_answer(answer)}")


def ensure_username_available(cur, username: str, exclude_user_id: int | None = None) -> None:
    if exclude_user_id is None:
        row = cur.execute(
            "SELECT id FROM user_accounts WHERE lower(username) = lower(?) AND deleted_at IS NULL",
            (username,),
        ).fetchone()
    else:
        row = cur.execute(
            "SELECT id FROM user_accounts WHERE lower(username) = lower(?) AND id != ? AND deleted_at IS NULL",
            (username, exclude_user_id),
        ).fetchone()
    if row:
        raise HTTPException(status_code=409, detail="用户名已被使用")


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


def _token_version(cur, user_id: int) -> int:
    row = cur.execute("SELECT token_version FROM user_accounts WHERE id = ?", (user_id,)).fetchone()
    return int(row["token_version"] if row else 0)


def _issue_tokens(cur, user_id: int, user_uid: str, request: Request, device_name: str | None = None) -> dict:
    access_token = create_access_token(
        {"sub": user_uid, "typ": "access", "ver": _token_version(cur, user_id)},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token()
    expires_at = iso_datetime(utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    cur.execute(
        """
        INSERT INTO user_sessions(session_uid, user_id, refresh_token_hash, device_name, user_agent,
                                  ip_address, expires_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            random_uid("sess"),
            user_id,
            hash_token(refresh_token),
            device_name or "当前设备",
            request.headers.get("user-agent", ""),
            _client_ip(request),
            expires_at,
        ),
    )
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "Bearer",
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    with db_cursor() as cur:
        user = cur.execute(
            """
            SELECT id, user_uid, username, email, phone, account_status, token_version,
                   email_verified, phone_verified, last_login_at, created_at
            FROM user_accounts
            WHERE user_uid = ? AND deleted_at IS NULL
            """,
            (payload.get("sub"),),
        ).fetchone()
    if not user or user["account_status"] != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    if int(payload.get("ver", -1)) != int(user["token_version"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    return user


@router.get("/username-available")
def username_available(username: str = Query(min_length=3, max_length=32)):
    normalized = normalize_username(username)
    with db_cursor() as cur:
        ensure_username_available(cur, normalized)
    return {"available": True, "username": normalized}


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, request: Request):
    username = normalize_username(payload.username)
    email = normalize_email(payload.email)
    display_name = (payload.displayName or username).strip() or username
    user_uid = random_uid("usr")
    try:
        with db_cursor() as cur:
            ensure_username_available(cur, username)
            cur.execute(
                """
                INSERT INTO user_accounts(user_uid, username, email, account_status)
                VALUES (?, ?, ?, 'active')
                """,
                (user_uid, username, email),
            )
            user_id = cur.lastrowid
            cur.execute(
                "INSERT INTO user_auth_passwords(user_id, password_hash) VALUES (?, ?)",
                (user_id, hash_password(payload.password)),
            )
            cur.execute(
                "INSERT INTO user_profiles(user_id, display_name) VALUES (?, ?)",
                (user_id, display_name),
            )
            cur.execute("INSERT INTO user_preferences(user_id) VALUES (?)", (user_id,))
            cur.execute(
                """
                INSERT INTO user_role_assignments(user_id, role_id)
                SELECT ?, id FROM roles WHERE code = 'user'
                """,
                (user_id,),
            )
            tokens = _issue_tokens(cur, user_id, user_uid, request, "注册设备")
            user = cur.execute(
                """
                SELECT id, user_uid, username, email, phone, account_status, token_version,
                       email_verified, phone_verified, last_login_at, created_at
                FROM user_accounts WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="用户名或邮箱已被使用")
    return {"user": _public_user(user), **tokens}


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    identifier = payload.identifier.strip()
    lookup = identifier.lower() if "@" in identifier else identifier
    login_failed = False
    with db_cursor() as cur:
        user = cur.execute(
            """
            SELECT id, user_uid, username, email, phone, account_status, token_version,
                   email_verified, phone_verified, last_login_at, created_at
            FROM user_accounts
            WHERE (username = ? OR lower(email) = lower(?) OR phone = ?) AND deleted_at IS NULL
            """,
            (identifier, lookup, identifier),
        ).fetchone()
        password_row = None
        if user:
            password_row = cur.execute(
                "SELECT password_hash, failed_attempts FROM user_auth_passwords WHERE user_id = ?",
                (user["id"],),
            ).fetchone()
        ok = bool(user and user["account_status"] == "active" and password_row and verify_password(payload.password, password_row["password_hash"]))
        cur.execute(
            """
            INSERT INTO user_login_logs(user_id, login_identifier, result, failure_reason, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"] if user else None,
                identifier,
                "success" if ok else "failed",
                None if ok else "账号或密码错误",
                _client_ip(request),
                request.headers.get("user-agent", ""),
            ),
        )
        if not ok:
            if user:
                cur.execute(
                    "UPDATE user_auth_passwords SET failed_attempts = failed_attempts + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user["id"],),
                )
            login_failed = True
            tokens = None
        else:
            cur.execute(
                """
                UPDATE user_accounts
                SET last_login_at = CURRENT_TIMESTAMP, last_login_ip = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (_client_ip(request), user["id"]),
            )
            cur.execute(
                "UPDATE user_auth_passwords SET failed_attempts = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user["id"],),
            )
            tokens = _issue_tokens(cur, user["id"], user["user_uid"], request, payload.deviceName)
    if login_failed:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return {"user": _public_user(user), **tokens}


@router.post("/password-reset/security/start")
def password_reset_security_start(payload: PasswordResetStartRequest):
    identifier = payload.identifier.strip()
    lookup = identifier.lower() if "@" in identifier else identifier
    with db_cursor() as cur:
        user = cur.execute(
            """
            SELECT id, username, email, phone, account_status
            FROM user_accounts
            WHERE (username = ? OR lower(email) = lower(?) OR phone = ?) AND deleted_at IS NULL
            """,
            (identifier, lookup, identifier),
        ).fetchone()
        if not user or user["account_status"] != "active":
            raise HTTPException(status_code=404, detail="未找到可用账号")
        questions = cur.execute(
            """
            SELECT question_order, question_text
            FROM user_security_questions
            WHERE user_id = ?
            ORDER BY question_order
            """,
            (user["id"],),
        ).fetchall()
        if not questions:
            raise HTTPException(status_code=409, detail="该账号尚未设置密保问题")
        reset_uid = random_uid("reset")
        cur.execute(
            """
            INSERT INTO user_verification_tokens(token_uid, user_id, target, purpose, token_hash, expires_at)
            VALUES (?, ?, ?, 'password_reset', ?, ?)
            """,
            (
                reset_uid,
                user["id"],
                f"security-challenge:{identifier}",
                hash_token(reset_uid),
                iso_datetime(utc_now() + timedelta(minutes=10)),
            ),
        )
    return {
        "resetUid": reset_uid,
        "questions": [
            {"order": row["question_order"], "question": row["question_text"]}
            for row in questions
        ],
        "expiresIn": 600,
    }


@router.post("/password-reset/security/verify")
def password_reset_security_verify(payload: PasswordResetVerifyRequest):
    with db_cursor() as cur:
        challenge = cur.execute(
            """
            SELECT token_uid, user_id
            FROM user_verification_tokens
            WHERE token_uid = ? AND token_hash = ? AND purpose = 'password_reset'
              AND consumed_at IS NULL AND expires_at > CURRENT_TIMESTAMP
            """,
            (payload.resetUid, hash_token(payload.resetUid)),
        ).fetchone()
        if not challenge:
            raise HTTPException(status_code=401, detail="找回密码会话已失效")
        questions = cur.execute(
            """
            SELECT question_order, answer_hash
            FROM user_security_questions
            WHERE user_id = ?
            ORDER BY question_order
            """,
            (challenge["user_id"],),
        ).fetchall()
        if len(payload.answers) != len(questions):
            raise HTTPException(status_code=422, detail="密保答案数量不匹配")
        for answer, question in zip(payload.answers, questions):
            if hash_security_answer(answer) != question["answer_hash"]:
                raise HTTPException(status_code=401, detail="密保答案不正确")
        cur.execute(
            "UPDATE user_verification_tokens SET consumed_at = CURRENT_TIMESTAMP WHERE token_uid = ?",
            (payload.resetUid,),
        )
        reset_token = create_refresh_token()
        reset_uid = random_uid("resetok")
        cur.execute(
            """
            INSERT INTO user_verification_tokens(token_uid, user_id, target, purpose, token_hash, expires_at)
            VALUES (?, ?, 'security-verified', 'password_reset', ?, ?)
            """,
            (
                reset_uid,
                challenge["user_id"],
                hash_token(reset_token),
                iso_datetime(utc_now() + timedelta(minutes=10)),
            ),
        )
    return {"resetToken": reset_token, "expiresIn": 600}


@router.post("/password-reset/security/confirm")
def password_reset_security_confirm(payload: PasswordResetConfirmRequest):
    with db_cursor() as cur:
        token = cur.execute(
            """
            SELECT token_uid, user_id
            FROM user_verification_tokens
            WHERE token_hash = ? AND purpose = 'password_reset' AND target = 'security-verified'
              AND consumed_at IS NULL AND expires_at > CURRENT_TIMESTAMP
            """,
            (hash_token(payload.resetToken),),
        ).fetchone()
        if not token:
            raise HTTPException(status_code=401, detail="重置密码令牌无效或已过期")
        cur.execute(
            """
            UPDATE user_auth_passwords
            SET password_hash = ?, failed_attempts = 0, locked_until = NULL,
                password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (hash_password(payload.newPassword), token["user_id"]),
        )
        cur.execute(
            """
            UPDATE user_accounts
            SET token_version = token_version + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (token["user_id"],),
        )
        cur.execute(
            "UPDATE user_sessions SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP WHERE user_id = ? AND is_revoked = 0",
            (token["user_id"],),
        )
        cur.execute(
            "UPDATE user_verification_tokens SET consumed_at = CURRENT_TIMESTAMP WHERE token_uid = ?",
            (token["token_uid"],),
        )
    return {"status": "ok", "message": "密码已重置，请重新登录"}


@router.post("/refresh")
def refresh(payload: RefreshRequest, request: Request):
    with db_cursor() as cur:
        session = cur.execute(
            """
            SELECT s.id, s.user_id, u.user_uid, u.account_status, u.token_version
            FROM user_sessions s
            JOIN user_accounts u ON u.id = s.user_id
            WHERE s.refresh_token_hash = ? AND s.is_revoked = 0 AND s.expires_at > CURRENT_TIMESTAMP
            """,
            (hash_token(payload.refreshToken),),
        ).fetchone()
        if not session or session["account_status"] != "active":
            raise HTTPException(status_code=401, detail="刷新令牌无效")
        cur.execute(
            "UPDATE user_sessions SET last_seen_at = CURRENT_TIMESTAMP, ip_address = ?, user_agent = ? WHERE id = ?",
            (_client_ip(request), request.headers.get("user-agent", ""), session["id"]),
        )
        access_token = create_access_token(
            {"sub": session["user_uid"], "typ": "access", "ver": int(session["token_version"])},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
    return {"accessToken": access_token, "tokenType": "Bearer", "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60}


@router.post("/logout")
def logout(payload: RefreshRequest, current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE user_sessions
            SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND refresh_token_hash = ?
            """,
            (current_user["id"], hash_token(payload.refreshToken)),
        )
    return {"status": "ok"}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"user": _public_user(current_user)}
