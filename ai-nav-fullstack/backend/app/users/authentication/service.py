import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, LOGIN_LOCK_MINUTES, LOGIN_MAX_FAILED_ATTEMPTS, PRIVACY_POLICY_VERSION, REFRESH_TOKEN_EXPIRE_DAYS
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    iso_datetime,
    needs_password_rehash,
    random_uid,
    utc_now,
    verify_password,
)
from app.users.account.service import normalize_username
from app.users.account.identity import normalize_email, normalize_login_identifier, normalize_phone
from app.users.audit.service import AuditService, get_audit_service
from app.users.authentication.ports import AuthenticationRepository
from app.users.authentication.repositories.sqlite import SQLiteAuthenticationRepository
from app.users.common import UsersError
from app.users.privacy.service import PrivacyService, get_privacy_service
from app.users.security.service import hash_security_answer, validate_password_strength


@dataclass(frozen=True)
class RequestContext:
    ip_address: str
    user_agent: str


def public_user(row: dict) -> dict:
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


class AuthenticationService:
    def __init__(
        self,
        repository: AuthenticationRepository,
        audit: AuditService | None = None,
        privacy: PrivacyService | None = None,
    ):
        self.repository = repository
        self.audit = audit or get_audit_service()
        self.privacy = privacy or get_privacy_service()

    def _audit(self, event: str, user_id: int, user_uid: str, context: RequestContext, metadata: dict) -> None:
        self.audit.record(
            event,
            actor_user_id=user_id,
            target_user_id=user_id,
            resource_id=user_uid,
            metadata=metadata,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
        )

    def username_available(self, username: str) -> dict:
        normalized = normalize_username(username)
        if not self.repository.is_username_available(normalized):
            raise UsersError("USERNAME_TAKEN", "用户名已被使用", 409)
        return {"available": True, "username": normalized}

    def _issue_tokens(
        self,
        user_id: int,
        user_uid: str,
        context: RequestContext,
        device_name: str | None = None,
        persistent: bool = False,
    ) -> dict:
        access_token = create_access_token(
            {"sub": user_uid, "typ": "access", "ver": self.repository.get_token_version(user_id)},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token()
        self.repository.create_session({
            "sessionUid": random_uid("sess"),
            "userId": user_id,
            "refreshTokenHash": hash_token(refresh_token),
            "deviceName": device_name or "当前设备",
            "userAgent": context.user_agent,
            "ipAddress": context.ip_address,
            "expiresAt": iso_datetime(utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)),
            "isPersistent": persistent,
        })
        return {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "tokenType": "Bearer",
            "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    def register(self, item: dict, context: RequestContext) -> dict:
        if item.get("privacyAccepted") is not True:
            raise UsersError("PRIVACY_CONSENT_REQUIRED", "请先阅读并同意隐私政策与服务协议", 422)
        username = normalize_username(item["username"])
        email = normalize_email(item.get("email"))
        phone = normalize_phone(item.get("phone"))
        display_name = (item.get("displayName") or username).strip() or username
        validate_password_strength(item["password"])
        if not self.repository.is_username_available(username):
            raise UsersError("USERNAME_TAKEN", "用户名或邮箱已被使用", 409)
        try:
            user = self.repository.register_user({
                "userUid": random_uid("usr"),
                "username": username,
                "email": email,
                "phone": phone,
                "displayName": display_name,
                "passwordHash": hash_password(item["password"]),
                "privacyConsentEventUid": random_uid("cons"),
                "privacyPolicyVersion": PRIVACY_POLICY_VERSION,
            })
        except sqlite3.IntegrityError as exc:
            raise UsersError("ACCOUNT_CONFLICT", "用户名或邮箱已被使用", 409) from exc
        tokens = self._issue_tokens(user["id"], user["user_uid"], context, "注册设备")
        self._audit("users.auth.registered", user["id"], user["user_uid"], context, {"sessionIssued": True})
        return {"user": public_user(user), **tokens}

    def login(self, item: dict, context: RequestContext) -> dict:
        if item.get("privacyAccepted") is not True:
            raise UsersError("PRIVACY_CONSENT_REQUIRED", "请先阅读并同意隐私政策与服务协议", 422)
        identifier = normalize_login_identifier(item["identifier"])
        user = self.repository.find_login_user(identifier)
        locked = bool(user and user.get("lockedUntil") and user["lockedUntil"] > iso_datetime(utc_now()))
        ok = bool(
            user
            and not locked
            and user["account_status"] == "active"
            and user.get("password_hash")
            and verify_password(item["password"], user["password_hash"])
        )
        if not ok:
            self.repository.record_login(
                user["id"] if user else None,
                identifier,
                False,
                "账号或密码错误",
                context.ip_address,
                context.user_agent,
            )
            if user and not locked:
                self.repository.increment_failed_attempts(
                    user["id"],
                    LOGIN_MAX_FAILED_ATTEMPTS,
                    iso_datetime(utc_now() + timedelta(minutes=LOGIN_LOCK_MINUTES)),
                )
            raise UsersError("INVALID_CREDENTIALS", "账号或密码错误", 401)
        if not (
            user.get("privacyConsentAction") == "granted"
            and user.get("privacyConsentPolicyVersion") == PRIVACY_POLICY_VERSION
        ):
            self.privacy.set_consent(
                user["id"],
                "privacy_policy",
                PRIVACY_POLICY_VERSION,
                True,
                source="login",
            )
            self.audit.record(
                "users.privacy.consent_updated",
                actor_user_id=user["id"],
                target_user_id=user["id"],
                resource_id="privacy_policy",
                metadata={
                    "consentType": "privacy_policy",
                    "policyVersion": PRIVACY_POLICY_VERSION,
                    "status": "granted",
                },
                ip_address=context.ip_address,
                user_agent=context.user_agent,
            )
        if needs_password_rehash(user["password_hash"]):
            self.repository.rehash_password(user["id"], hash_password(item["password"]))
        self.repository.record_login(
            user["id"],
            identifier,
            True,
            None,
            context.ip_address,
            context.user_agent,
        )
        self.repository.mark_login_success(user["id"], context.ip_address)
        tokens = self._issue_tokens(
            user["id"],
            user["user_uid"],
            context,
            item.get("deviceName"),
            persistent=bool(item.get("rememberMe", False)),
        )
        self._audit("users.auth.login_succeeded", user["id"], user["user_uid"], context, {"sessionIssued": True})
        return {"user": public_user(user), **tokens}

    def current_user_from_token(self, token: str) -> dict:
        payload = decode_access_token(token)
        if not payload or payload.get("typ") != "access":
            raise UsersError("AUTH_TOKEN_INVALID", "登录已失效", 401)
        user = self.repository.get_current_user_by_uid(payload.get("sub"))
        if not user or user["account_status"] != "active":
            raise UsersError("ACCOUNT_UNAVAILABLE", "账号不可用", 401)
        if int(payload.get("ver", -1)) != int(user["token_version"]):
            raise UsersError("AUTH_TOKEN_EXPIRED", "登录已失效", 401)
        return user

    def refresh(self, refresh_token: str, context: RequestContext) -> dict:
        result, _ = self.refresh_with_cookie_policy(refresh_token, context)
        return result

    def refresh_with_cookie_policy(self, refresh_token: str, context: RequestContext) -> tuple[dict, bool]:
        refresh_hash = hash_token(refresh_token)
        session = self.repository.find_refresh_session(refresh_hash)
        if not session:
            previous = self.repository.find_any_refresh_session(refresh_hash)
            if previous and previous.get("revokedReason") == "rotated":
                self.repository.revoke_token_family(previous["userId"], previous["tokenFamilyUid"], "replay_detected")
                raise UsersError("REFRESH_TOKEN_REPLAYED", "刷新令牌已被重复使用，请重新登录", 401)
            raise UsersError("REFRESH_TOKEN_INVALID", "刷新令牌无效", 401)
        if not session or session["accountStatus"] != "active":
            raise UsersError("REFRESH_TOKEN_INVALID", "刷新令牌无效", 401)
        new_refresh_token = create_refresh_token()
        self.repository.rotate_refresh_session(
            session["id"],
            {
                "sessionUid": random_uid("sess"),
                "refreshTokenHash": hash_token(new_refresh_token),
                "deviceName": session.get("deviceName") or "当前设备",
                "userAgent": context.user_agent,
                "ipAddress": context.ip_address,
                "expiresAt": iso_datetime(utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)),
                "isPersistent": bool(session.get("isPersistent", False)),
            },
        )
        access_token = create_access_token(
            {"sub": session["userUid"], "typ": "access", "ver": int(session["tokenVersion"])},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        self._audit(
            "users.auth.session_refreshed",
            session["userId"],
            session["userUid"],
            context,
            {"rotation": True},
        )
        return {
            "accessToken": access_token,
            "refreshToken": new_refresh_token,
            "tokenType": "Bearer",
            "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }, bool(session.get("isPersistent", False))

    def logout(
        self,
        user_id: int,
        refresh_token: str,
        user_uid: str | None = None,
        context: RequestContext | None = None,
    ) -> dict:
        self.repository.revoke_refresh_token(user_id, hash_token(refresh_token))
        if user_uid and context:
            self._audit("users.auth.session_logged_out", user_id, user_uid, context, {"scope": "current"})
        return {"status": "ok"}

    def password_reset_security_start(self, identifier: str, context: RequestContext | None = None) -> dict:
        reset_uid = random_uid("reset")
        result = self.repository.start_security_reset(
            identifier.strip(),
            reset_uid,
            hash_token(reset_uid),
            iso_datetime(utc_now() + timedelta(minutes=10)),
        )
        if not result:
            raise UsersError("RESET_ACCOUNT_NOT_FOUND", "未找到可用账号", 404)
        user, questions = result
        if not questions:
            raise UsersError("SECURITY_QUESTIONS_NOT_CONFIGURED", "该账号尚未设置密保问题", 409)
        if context:
            self._audit(
                "users.auth.password_reset_started",
                user["id"],
                user["userUid"],
                context,
                {"stage": "started"},
            )
        return {
            "resetUid": reset_uid,
            "questions": [{"order": row["questionOrder"], "question": row["question"]} for row in questions],
            "expiresIn": 600,
        }

    def password_reset_security_verify(
        self,
        reset_uid: str,
        answers: list[str],
        context: RequestContext | None = None,
    ) -> dict:
        result = self.repository.verify_security_reset(reset_uid, hash_token(reset_uid))
        if not result:
            raise UsersError("RESET_SESSION_INVALID", "找回密码会话已失效", 401)
        challenge, questions = result
        if len(answers) != len(questions):
            raise UsersError("SECURITY_ANSWER_COUNT_MISMATCH", "密保答案数量不匹配", 422)
        for answer, question in zip(answers, questions):
            if hash_security_answer(answer) != question["answerHash"]:
                raise UsersError("SECURITY_ANSWER_INVALID", "密保答案不正确", 401)
        reset_token = create_refresh_token()
        user = self.repository.consume_reset_challenge(
            reset_uid,
            random_uid("resetok"),
            hash_token(reset_token),
            iso_datetime(utc_now() + timedelta(minutes=10)),
        )
        if context:
            self._audit(
                "users.auth.password_reset_verified",
                user["userId"],
                user["userUid"],
                context,
                {"stage": "verified"},
            )
        return {
            "resetToken": reset_token,
            "expiresIn": 600,
        }

    def password_reset_security_confirm(
        self,
        reset_token: str,
        new_password: str,
        context: RequestContext | None = None,
    ) -> dict:
        validate_password_strength(new_password)
        user = self.repository.confirm_security_reset(hash_token(reset_token), hash_password(new_password))
        if not user:
            raise UsersError("RESET_TOKEN_INVALID", "重置密码令牌无效或已过期", 401)
        if context:
            self._audit(
                "users.auth.password_reset_completed",
                user["userId"],
                user["userUid"],
                context,
                {"stage": "completed", "sessionsRevoked": True},
            )
        return {
            "status": "ok",
            "message": "密码已重置，请重新登录",
        }


@lru_cache(maxsize=1)
def get_authentication_service() -> AuthenticationService:
    return AuthenticationService(SQLiteAuthenticationRepository())
