import re
import sqlite3
from functools import lru_cache

from app.users.account.ports import AccountRepository
from app.users.account.repositories.sqlite import SQLiteAccountRepository
from app.users.common import UsersError
from app.core.security import verify_password
from app.users.account.identity import normalize_email, normalize_phone


USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5-]{3,32}$")
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
SENSITIVE_USERNAME_WORDS = {"管理员", "官方", "客服", "系统", "平台", "运营", "审核", "root", "admin"}


def normalize_username(username: str) -> str:
    value = username.strip()
    if not USERNAME_RE.match(value):
        raise UsersError("USERNAME_INVALID", "用户名只能包含中文、字母、数字、下划线和短横线，长度为 3-32 位", 422)
    lower_value = value.lower()
    if lower_value in RESERVED_USERNAMES:
        raise UsersError("USERNAME_RESERVED", "该用户名为系统保留名称", 422)
    if any(word in lower_value or word in value for word in SENSITIVE_USERNAME_WORDS):
        raise UsersError("USERNAME_SENSITIVE", "用户名包含不适合使用的词", 422)
    return value


class AccountService:
    def __init__(self, repository: AccountRepository):
        self.repository = repository

    def get_account(self, user_id: int) -> dict:
        account = self.repository.get_account(user_id)
        if not account:
            raise UsersError("ACCOUNT_NOT_FOUND", "用户账号不存在", 404)
        return {"account": account}

    def update_account(self, user_id: int, item: dict) -> dict:
        current = self.repository.get_account(user_id)
        if not current:
            raise UsersError("ACCOUNT_NOT_FOUND", "用户账号不存在", 404)
        username = normalize_username(item["username"]) if "username" in item else current["username"]
        email = normalize_email(item.get("email")) if "email" in item else current["email"]
        phone = normalize_phone(item.get("phone")) if "phone" in item else current["phone"]
        changed_fields = [
            field
            for field, before, after in (
                ("username", current["username"], username),
                ("email", current["email"], email),
                ("phone", current["phone"], phone),
            )
            if before != after
        ]
        if "username" in changed_fields and not self.repository.is_username_available(username, user_id):
            raise UsersError("USERNAME_TAKEN", "用户名已被使用", 409)
        if email and "email" in changed_fields and not self.repository.is_email_available(email, user_id):
            raise UsersError("EMAIL_TAKEN", "邮箱已被其他账号绑定", 409)
        if phone and "phone" in changed_fields and not self.repository.is_phone_available(phone, user_id):
            raise UsersError("PHONE_TAKEN", "手机号已被其他账号绑定", 409)
        if any(field in changed_fields for field in ("email", "phone")):
            password_hash = self.repository.get_password_hash(user_id)
            if not password_hash or not verify_password(item.get("currentPassword") or "", password_hash):
                raise UsersError("CURRENT_PASSWORD_INVALID", "修改邮箱或手机号需要验证当前密码", 401)
        if not changed_fields:
            return {"account": current, "meta": {"changedFields": []}}
        try:
            account = self.repository.update_account(user_id, username, email, phone)
        except sqlite3.IntegrityError as exc:
            raise UsersError("ACCOUNT_IDENTITY_TAKEN", "用户名、邮箱或手机号已被使用", 409) from exc
        return {"account": account, "meta": {"changedFields": changed_fields}}


@lru_cache(maxsize=1)
def get_account_service() -> AccountService:
    return AccountService(SQLiteAccountRepository())
