import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import PASSWORD_HASH_ROUNDS, SECRET_KEY


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def random_uid(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


def _password_hash_parts(password_hash: str) -> tuple[str, int, bytes, bytes] | None:
    try:
        algo, rounds, salt_b64, digest_b64 = password_hash.split("$", 3)
        return (
            algo,
            int(rounds),
            base64.urlsafe_b64decode(salt_b64.encode("ascii")),
            base64.urlsafe_b64decode(digest_b64.encode("ascii")),
        )
    except Exception:
        return None


def hash_password(password: str, rounds: int = PASSWORD_HASH_ROUNDS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return "pbkdf2_sha256${}${}${}".format(
        rounds,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    parts = _password_hash_parts(password_hash)
    if not parts:
        return False
    algo, rounds, salt, expected = parts
    if algo != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(actual, expected)


def needs_password_rehash(password_hash: str) -> bool:
    parts = _password_hash_parts(password_hash)
    if not parts:
        return True
    algo, rounds, _, _ = parts
    return algo != "pbkdf2_sha256" or rounds < PASSWORD_HASH_ROUNDS


def hash_token(token: str) -> str:
    return hmac.new(SECRET_KEY.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def create_access_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    token_payload = dict(payload)
    token_payload["exp"] = int((utc_now() + expires_delta).timestamp())
    body = _b64url(json.dumps(token_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signature = hmac.new(SECRET_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url(signature)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(SECRET_KEY.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        actual = _b64url_decode(signature)
        if not hmac.compare_digest(actual, expected):
            return None
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(utc_now().timestamp()):
            return None
        return payload
    except Exception:
        return None


def create_refresh_token() -> str:
    return secrets.token_urlsafe(40)
