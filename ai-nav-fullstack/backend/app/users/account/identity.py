import re

from app.users.common import UsersError


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
E164_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
CN_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def normalize_email(email: str | None) -> str | None:
    if not email or not email.strip():
        return None
    value = email.strip().lower()
    if not EMAIL_RE.fullmatch(value):
        raise UsersError("EMAIL_INVALID", "邮箱格式不正确", 422)
    return value


def normalize_phone(phone: str | None) -> str | None:
    if not phone or not phone.strip():
        return None
    value = re.sub(r"[\s()\-]", "", phone.strip())
    if CN_PHONE_RE.fullmatch(value):
        return f"+86{value}"
    if value.startswith("+86") and CN_PHONE_RE.fullmatch(value[3:]):
        return value
    if not E164_PHONE_RE.fullmatch(value):
        raise UsersError("PHONE_INVALID", "手机号格式不正确，请填写中国大陆手机号或 E.164 国际号码", 422)
    return value


def normalize_login_identifier(identifier: str) -> str:
    value = identifier.strip()
    compact = re.sub(r"[\s()\-]", "", value)
    if compact.startswith("+") or CN_PHONE_RE.fullmatch(compact):
        return normalize_phone(value) or value
    return value
