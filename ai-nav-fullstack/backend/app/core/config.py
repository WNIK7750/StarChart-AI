from pathlib import Path
import os
from ipaddress import ip_network


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


DEV_SECRET_KEY = "dev-secret-change-before-production"


def validate_runtime_security(
    environment: str,
    secret_key: str,
    cors_origins: tuple[str, ...],
    refresh_cookie_secure: bool,
) -> None:
    if environment not in {"development", "test", "production"}:
        raise RuntimeError("AI_NAV_ENV must be development, test, or production")
    if "*" in cors_origins:
        raise RuntimeError("AI_NAV_CORS_ALLOW_ORIGINS cannot contain wildcard origins")
    if environment == "production":
        if secret_key == DEV_SECRET_KEY or len(secret_key) < 32:
            raise RuntimeError("Production AI_NAV_SECRET_KEY must be a non-default value of at least 32 characters")
        if not refresh_cookie_secure:
            raise RuntimeError("Production requires AI_NAV_REFRESH_COOKIE_SECURE=1")


BASE_DIR = Path(__file__).resolve().parents[3]
DATABASE_PATH = Path(os.getenv("AI_NAV_DATABASE_PATH", str(BASE_DIR / "database" / "ai_nav.sqlite3"))).expanduser().resolve()
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"
LEARNING_CONTENT_PATH = BASE_DIR / "database" / "learning_content.sql"
MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"

API_PREFIX = "/api/v1"
APP_NAME = "AI Knowledge Navigation API"
APP_ENV = os.getenv("AI_NAV_ENV", "development").strip().lower()
SECRET_KEY = os.getenv("AI_NAV_SECRET_KEY", DEV_SECRET_KEY).strip()
CORS_ALLOW_ORIGINS = _env_csv(
    "AI_NAV_CORS_ALLOW_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:8088,http://localhost:8088",
)
TRUSTED_PROXY_CIDRS = _env_csv("AI_NAV_TRUSTED_PROXY_CIDRS")
for _trusted_proxy_cidr in TRUSTED_PROXY_CIDRS:
    try:
        ip_network(_trusted_proxy_cidr, strict=False)
    except ValueError as exc:
        raise RuntimeError(f"Invalid AI_NAV_TRUSTED_PROXY_CIDRS entry: {_trusted_proxy_cidr}") from exc
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
PASSWORD_HASH_ROUNDS = int(os.getenv("AI_NAV_PASSWORD_HASH_ROUNDS", "180000"))
ACCOUNT_DELETION_GRACE_DAYS = int(os.getenv("AI_NAV_ACCOUNT_DELETION_GRACE_DAYS", "7"))
ACCOUNT_DELETION_RETENTION_DAYS = int(os.getenv("AI_NAV_ACCOUNT_DELETION_RETENTION_DAYS", "30"))
PRIVACY_POLICY_VERSION = os.getenv("AI_NAV_PRIVACY_POLICY_VERSION", "2026-07-01")
AGENT_MEMORY_POLICY_VERSION = os.getenv("AI_NAV_AGENT_MEMORY_POLICY_VERSION", "2026-07-01")
LOGIN_MAX_FAILED_ATTEMPTS = int(os.getenv("AI_NAV_LOGIN_MAX_FAILED_ATTEMPTS", "5"))
LOGIN_LOCK_MINUTES = int(os.getenv("AI_NAV_LOGIN_LOCK_MINUTES", "15"))
REFRESH_COOKIE_NAME = os.getenv("AI_NAV_REFRESH_COOKIE_NAME", "ai_nav_refresh_token")
REFRESH_COOKIE_PATH = os.getenv("AI_NAV_REFRESH_COOKIE_PATH", f"{API_PREFIX}/auth")
REFRESH_COOKIE_SAMESITE = os.getenv("AI_NAV_REFRESH_COOKIE_SAMESITE", "lax")
REFRESH_COOKIE_SECURE = _env_bool("AI_NAV_REFRESH_COOKIE_SECURE", "0")
REFRESH_COOKIE_MAX_AGE_SECONDS = int(os.getenv("AI_NAV_REFRESH_COOKIE_MAX_AGE_SECONDS", str(REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)))
RESET_DATABASE_ON_START = os.getenv("RESET_DATABASE_ON_START", "0") == "1"
AVATAR_MAX_UPLOAD_BYTES = int(os.getenv("AVATAR_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
AVATAR_MAX_OUTPUT_BYTES = int(os.getenv("AVATAR_MAX_OUTPUT_BYTES", str(360 * 1024)))
AVATAR_MAX_DIMENSION = int(os.getenv("AVATAR_MAX_DIMENSION", "512"))
AVATAR_MAX_SOURCE_PIXELS = int(os.getenv("AVATAR_MAX_SOURCE_PIXELS", "20000000"))

validate_runtime_security(APP_ENV, SECRET_KEY, CORS_ALLOW_ORIGINS, REFRESH_COOKIE_SECURE)
