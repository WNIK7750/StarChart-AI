from typing import Any

from app.users.audit.events import AuditEventSpec


SENSITIVE_KEY_PARTS = {
    "answer",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
}


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:160]
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in list(value)[:20] if isinstance(item, (str, bool, int, float))]
    return None


def sanitize_audit_metadata(spec: AuditEventSpec, metadata: dict[str, Any] | None) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        normalized = key.lower()
        if key not in spec.allowed_metadata or any(part in normalized for part in SENSITIVE_KEY_PARTS):
            continue
        safe = _safe_value(value)
        if safe is not None:
            clean[key] = safe
    return clean
