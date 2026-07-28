from pathlib import Path
import os
import re
from dataclasses import dataclass, field
from ipaddress import ip_address, ip_network
from math import isfinite
from urllib.parse import urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
# Local development convenience only. Existing process/deployment variables win,
# so production can keep injecting secrets through its own secret manager.
if os.getenv("AI_NAV_DISABLE_DOTENV", "0").strip().lower() not in {"1", "true", "yes", "on"}:
    load_dotenv(BASE_DIR / ".env", override=False)


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


DEV_SECRET_KEY = "dev-secret-change-before-production"
AGENT_STAGE1_DEFAULT_MODEL = "qwen3.5-flash"
AGENT_STAGE1_UPGRADE_MODEL = "qwen3.7-plus"
DEPLOYMENT_PROFILES = frozenset(
    {"development", "test", "http_test", "provider_preview", "production"}
)


def normalize_public_base_path(value: str) -> str:
    """Return a canonical, relative public deployment prefix."""
    if not isinstance(value, str):
        raise RuntimeError("AI_NAV_PUBLIC_BASE_PATH must be a path string")
    normalized = value.strip()
    if not normalized:
        return ""
    if (
        not normalized.startswith("/")
        or normalized.startswith("//")
        or "\\" in normalized
        or "?" in normalized
        or "#" in normalized
        or "://" in normalized
    ):
        raise RuntimeError("AI_NAV_PUBLIC_BASE_PATH must be a relative path prefix")
    path_parts = normalized.split("/")
    if any(part == ".." for part in path_parts):
        raise RuntimeError("AI_NAV_PUBLIC_BASE_PATH cannot contain parent traversal")
    return normalized.rstrip("/")


def _normalize_host(value: str, setting_name: str) -> str:
    host = value.strip().lower().rstrip(".")
    if not host:
        raise RuntimeError(f"{setting_name} contains an invalid host")
    try:
        return ip_address(host).compressed
    except ValueError:
        pass
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise RuntimeError(f"{setting_name} contains an invalid host") from exc
    labels = ascii_host.split(".")
    if (
        len(ascii_host) > 253
        or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not re.fullmatch(r"[a-z0-9-]+", label)
            for label in labels
        )
    ):
        raise RuntimeError(f"{setting_name} contains an invalid host")
    return ascii_host


def _validate_explicit_origins(
    cors_origins: tuple[str, ...],
    *,
    required_scheme: str,
    profile_name: str,
) -> None:
    if not cors_origins:
        raise RuntimeError(
            f"{profile_name} AI_NAV_CORS_ALLOW_ORIGINS must list explicit {required_scheme.upper()} origins"
        )
    for origin in cors_origins:
        parsed = urlparse(origin)
        if (
            parsed.scheme != required_scheme
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise RuntimeError(
                f"{profile_name} AI_NAV_CORS_ALLOW_ORIGINS entries must be {required_scheme.upper()} origins without credentials or paths"
            )


def _validate_non_development_security(
    profile_name: str,
    secret_key: str,
    *,
    reset_database_on_start: bool,
    database_path: Path | None,
    upload_dir: Path | None,
    base_dir: Path,
) -> None:
    if secret_key == DEV_SECRET_KEY or len(secret_key) < 32:
        raise RuntimeError(
            f"{profile_name} AI_NAV_SECRET_KEY must be a non-default value of at least 32 characters"
        )
    if reset_database_on_start:
        raise RuntimeError(
            f"{profile_name} rejects RESET_DATABASE_ON_START=1; set RESET_DATABASE_ON_START=0"
        )
    resolved_base = base_dir.resolve()
    for setting_name, configured_path in (
        ("AI_NAV_DATABASE_PATH", database_path),
        ("AI_NAV_UPLOAD_DIR", upload_dir),
    ):
        if configured_path is None:
            continue
        resolved_path = configured_path.expanduser().resolve()
        if resolved_path == resolved_base or resolved_base in resolved_path.parents:
            raise RuntimeError(
                f"{profile_name} {setting_name} must use a persistent path outside the application source tree"
            )


def validate_runtime_security(
    environment: str,
    secret_key: str,
    cors_origins: tuple[str, ...],
    refresh_cookie_secure: bool,
    *,
    public_base_path: str = "",
    http_test_account_username: str = "",
    agent_provider: str = "deterministic",
    agent_provider_live_enabled: bool = False,
    app_host: str = "127.0.0.1",
    app_port: int = 8088,
    reset_database_on_start: bool = False,
    database_path: Path | None = None,
    upload_dir: Path | None = None,
    base_dir: Path = BASE_DIR,
    trusted_proxy_cidrs: tuple[str, ...] = (),
    refresh_cookie_samesite: str = "lax",
    account_deletion_grace_days: int = 7,
    account_deletion_retention_days: int = 30,
    avatar_max_request_bytes: int = 2 * 1024 * 1024 + 64 * 1024,
    avatar_max_frames: int = 1,
    avatar_processing_timeout_seconds: float = 2.0,
) -> None:
    if environment not in DEPLOYMENT_PROFILES:
        raise RuntimeError(
            "AI_NAV_ENV must be development, test, http_test, provider_preview, or production"
        )
    if "*" in cors_origins:
        raise RuntimeError("AI_NAV_CORS_ALLOW_ORIGINS cannot contain wildcard origins")
    if refresh_cookie_samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("AI_NAV_REFRESH_COOKIE_SAMESITE must be lax, strict, or none")
    if refresh_cookie_samesite == "none" and not refresh_cookie_secure:
        raise RuntimeError("AI_NAV_REFRESH_COOKIE_SAMESITE=none requires AI_NAV_REFRESH_COOKIE_SECURE=1")
    if not 1 <= account_deletion_grace_days <= 30:
        raise RuntimeError("AI_NAV_ACCOUNT_DELETION_GRACE_DAYS must be between 1 and 30")
    if not account_deletion_grace_days <= account_deletion_retention_days <= 365:
        raise RuntimeError(
            "AI_NAV_ACCOUNT_DELETION_RETENTION_DAYS must be between the grace period and 365"
        )
    if not 1024 <= avatar_max_request_bytes <= 16 * 1024 * 1024:
        raise RuntimeError("AVATAR_MAX_REQUEST_BYTES must be between 1 KiB and 16 MiB")
    if not 1 <= avatar_max_frames <= 10:
        raise RuntimeError("AVATAR_MAX_FRAMES must be between 1 and 10")
    if not 0.05 <= avatar_processing_timeout_seconds <= 10:
        raise RuntimeError("AVATAR_PROCESSING_TIMEOUT_SECONDS must be between 0.05 and 10")
    if environment in DEPLOYMENT_PROFILES - {"development", "test"}:
        _validate_non_development_security(
            environment.replace("_", " ").title(),
            secret_key,
            reset_database_on_start=reset_database_on_start,
            database_path=database_path,
            upload_dir=upload_dir,
            base_dir=base_dir,
        )
    if environment == "production":
        if not refresh_cookie_secure:
            raise RuntimeError("Production requires AI_NAV_REFRESH_COOKIE_SECURE=1")
        _validate_explicit_origins(
            cors_origins, required_scheme="https", profile_name="Production"
        )
        for cidr in trusted_proxy_cidrs:
            network = ip_network(cidr, strict=False)
            if network.prefixlen == 0:
                raise RuntimeError(
                    "Production AI_NAV_TRUSTED_PROXY_CIDRS cannot trust the entire address space"
                )
    if environment == "http_test":
        _validate_explicit_origins(
            cors_origins, required_scheme="http", profile_name="HTTP test"
        )
        if refresh_cookie_secure:
            raise RuntimeError("HTTP test requires AI_NAV_REFRESH_COOKIE_SECURE=0")
        if refresh_cookie_samesite != "lax":
            raise RuntimeError("HTTP test requires AI_NAV_REFRESH_COOKIE_SAMESITE=lax")
        if normalize_public_base_path(public_base_path) != "/StarChart-AI":
            raise RuntimeError("HTTP test requires AI_NAV_PUBLIC_BASE_PATH=/StarChart-AI")
        if not http_test_account_username.strip():
            raise RuntimeError("HTTP test requires a non-empty HTTP_TEST_ACCOUNT_USERNAME")
        if agent_provider != "deterministic":
            raise RuntimeError("HTTP test requires AI_NAV_AGENT_PROVIDER=deterministic")
        if agent_provider_live_enabled:
            raise RuntimeError("HTTP test rejects a live Provider")
    if environment == "provider_preview":
        if not refresh_cookie_secure:
            raise RuntimeError("Provider preview requires AI_NAV_REFRESH_COOKIE_SECURE=1")
        _validate_explicit_origins(
            cors_origins, required_scheme="https", profile_name="Provider preview"
        )
        if _normalize_host(app_host, "AI_NAV_APP_HOST") != "127.0.0.1":
            raise RuntimeError("Provider preview requires AI_NAV_APP_HOST=127.0.0.1")
        if not 1 <= app_port <= 65535:
            raise RuntimeError("AI_NAV_APP_PORT must be between 1 and 65535")
        if agent_provider != "openai_compatible":
            raise RuntimeError("Provider preview requires AI_NAV_AGENT_PROVIDER=openai_compatible")


def validate_agent_provider_config(
    environment: str,
    provider: str,
    base_url: str,
    model: str,
    api_key: str,
    timeout_seconds: float,
    max_retries: int,
    max_output_tokens: int,
    max_output_chars: int,
    max_evidence_items: int,
    max_evidence_chars: int,
    allowed_hosts: tuple[str, ...] = (),
    live_enabled: bool = False,
    upgrade_model: str = AGENT_STAGE1_UPGRADE_MODEL,
    upgrade_ratio: float = 0.0,
    per_user_concurrency: int = 1,
    global_concurrency: int = 8,
    queue_limit: int = 32,
    queue_timeout_seconds: float = 3.0,
    max_input_tokens: int = 4000,
    input_cny_per_million: float = 0.2,
    output_cny_per_million: float = 2.0,
    per_request_cost_cny: float = 0.02,
    per_user_daily_cost_cny: float = 0.1,
    global_daily_cost_cny: float = 5.0,
    global_monthly_cost_cny: float = 80.0,
) -> None:
    if provider not in {"deterministic", "fake", "openai_compatible"}:
        raise RuntimeError(
            "AI_NAV_AGENT_PROVIDER must be deterministic, fake, or openai_compatible"
        )
    if environment in {"production", "provider_preview"} and provider == "fake":
        raise RuntimeError("Production and provider_preview cannot use AI_NAV_AGENT_PROVIDER=fake")
    if live_enabled and provider != "openai_compatible":
        raise RuntimeError(
            "AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=1 requires "
            "AI_NAV_AGENT_PROVIDER=openai_compatible"
        )
    if not 1 <= timeout_seconds <= 120:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_TIMEOUT_SECONDS must be between 1 and 120")
    if not 0 <= max_retries <= 1:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_MAX_RETRIES must be 0 or 1")
    if not 1 <= max_output_tokens <= 8192:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_MAX_OUTPUT_TOKENS must be between 1 and 8192")
    if not 100 <= max_output_chars <= 20000:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_MAX_OUTPUT_CHARS must be between 100 and 20000")
    if not 1 <= max_evidence_items <= 20:
        raise RuntimeError("AI_NAV_AGENT_MAX_EVIDENCE_ITEMS must be between 1 and 20")
    if not 500 <= max_evidence_chars <= 50000:
        raise RuntimeError("AI_NAV_AGENT_MAX_EVIDENCE_CHARS must be between 500 and 50000")
    if upgrade_model != AGENT_STAGE1_UPGRADE_MODEL:
        raise RuntimeError(
            "Stage 1 AI_NAV_AGENT_PROVIDER_UPGRADE_MODEL must remain qwen3.7-plus"
        )
    if upgrade_ratio != 0:
        raise RuntimeError(
            "Stage 1 AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO must remain 0 until evaluation approval"
        )
    if not 1 <= per_user_concurrency <= 4:
        raise RuntimeError("AI_NAV_AGENT_PER_USER_CONCURRENCY must be between 1 and 4")
    if not 1 <= global_concurrency <= 64:
        raise RuntimeError("AI_NAV_AGENT_GLOBAL_CONCURRENCY must be between 1 and 64")
    if per_user_concurrency > global_concurrency:
        raise RuntimeError("Agent per-user concurrency cannot exceed global concurrency")
    if not 0 <= queue_limit <= 1000:
        raise RuntimeError("AI_NAV_AGENT_QUEUE_LIMIT must be between 0 and 1000")
    if not 0 <= queue_timeout_seconds <= 30:
        raise RuntimeError("AI_NAV_AGENT_QUEUE_TIMEOUT_SECONDS must be between 0 and 30")
    if not 256 <= max_input_tokens <= 128000:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_MAX_INPUT_TOKENS must be between 256 and 128000")
    cost_limits = {
        "AI_NAV_AGENT_INPUT_CNY_PER_MILLION": input_cny_per_million,
        "AI_NAV_AGENT_OUTPUT_CNY_PER_MILLION": output_cny_per_million,
        "AI_NAV_AGENT_PER_REQUEST_COST_CNY": per_request_cost_cny,
        "AI_NAV_AGENT_PER_USER_DAILY_COST_CNY": per_user_daily_cost_cny,
        "AI_NAV_AGENT_GLOBAL_DAILY_COST_CNY": global_daily_cost_cny,
        "AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY": global_monthly_cost_cny,
    }
    if any(not isfinite(value) or value <= 0 for value in cost_limits.values()):
        raise RuntimeError("Agent price and cost limits must be finite positive numbers")
    if per_request_cost_cny > per_user_daily_cost_cny:
        raise RuntimeError("Agent per-request cost cannot exceed per-user daily cost")
    if per_user_daily_cost_cny > global_daily_cost_cny:
        raise RuntimeError("Agent per-user daily cost cannot exceed global daily cost")
    if global_daily_cost_cny > global_monthly_cost_cny:
        raise RuntimeError("Agent global daily cost cannot exceed global monthly cost")
    if provider != "openai_compatible":
        return
    if not base_url or not model or not api_key:
        raise RuntimeError(
            "openai_compatible requires AI_NAV_AGENT_PROVIDER_BASE_URL, "
            "AI_NAV_AGENT_PROVIDER_MODEL, and AI_NAV_AGENT_PROVIDER_API_KEY"
        )
    try:
        parsed = urlparse(base_url)
        provider_host = _normalize_host(
            parsed.hostname or "",
            "AI_NAV_AGENT_PROVIDER_BASE_URL",
        )
        parsed.port
    except ValueError as exc:
        raise RuntimeError(
            "AI_NAV_AGENT_PROVIDER_BASE_URL must be a valid absolute HTTP(S) URL"
        ) from exc
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_BASE_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("AI_NAV_AGENT_PROVIDER_BASE_URL cannot contain credentials, query, or fragment")
    if environment in {"production", "provider_preview"} and parsed.scheme != "https":
        raise RuntimeError("Production and provider_preview AI_NAV_AGENT_PROVIDER_BASE_URL must use HTTPS")
    if live_enabled and model != AGENT_STAGE1_DEFAULT_MODEL:
        raise RuntimeError(
            "Stage 1 live Provider model must remain qwen3.5-flash"
        )
    if environment in {"production", "provider_preview"}:
        normalized_hosts = {
            _normalize_host(host, "AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS")
            for host in allowed_hosts
        }
        if not normalized_hosts or provider_host not in normalized_hosts:
            raise RuntimeError(
                "Production provider host must be explicitly listed in "
                "AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS"
            )
        if live_enabled and not provider_host.endswith(".cn-beijing.maas.aliyuncs.com"):
            raise RuntimeError(
                "Stage 1 production and provider_preview Provider must use the approved Alibaba Cloud Beijing workspace host"
            )


@dataclass(frozen=True, slots=True)
class AgentProviderSettings:
    provider: str
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout_seconds: float = 8
    max_retries: int = 1
    max_output_tokens: int = 600
    max_output_chars: int = 6000
    max_evidence_items: int = 10
    max_evidence_chars: int = 12000
    allowed_hosts: tuple[str, ...] = ()
    live_enabled: bool = False
    upgrade_model: str = AGENT_STAGE1_UPGRADE_MODEL
    upgrade_ratio: float = 0.0
    per_user_concurrency: int = 1
    global_concurrency: int = 8
    queue_limit: int = 32
    queue_timeout_seconds: float = 3.0
    max_input_tokens: int = 4000
    input_cny_per_million: float = 0.2
    output_cny_per_million: float = 2.0
    per_request_cost_cny: float = 0.02
    per_user_daily_cost_cny: float = 0.1
    global_daily_cost_cny: float = 5.0
    global_monthly_cost_cny: float = 80.0


def get_agent_provider_settings(environment: str | None = None) -> AgentProviderSettings:
    try:
        settings = AgentProviderSettings(
            provider=os.getenv("AI_NAV_AGENT_PROVIDER", "deterministic").strip().lower(),
            base_url=os.getenv("AI_NAV_AGENT_PROVIDER_BASE_URL", "").strip(),
            model=os.getenv(
                "AI_NAV_AGENT_PROVIDER_MODEL",
                AGENT_STAGE1_DEFAULT_MODEL,
            ).strip(),
            api_key=os.getenv("AI_NAV_AGENT_PROVIDER_API_KEY", "").strip(),
            timeout_seconds=float(os.getenv("AI_NAV_AGENT_PROVIDER_TIMEOUT_SECONDS", "8")),
            max_retries=int(os.getenv("AI_NAV_AGENT_PROVIDER_MAX_RETRIES", "1")),
            max_output_tokens=int(os.getenv("AI_NAV_AGENT_PROVIDER_MAX_OUTPUT_TOKENS", "600")),
            max_output_chars=int(os.getenv("AI_NAV_AGENT_PROVIDER_MAX_OUTPUT_CHARS", "6000")),
            max_evidence_items=int(os.getenv("AI_NAV_AGENT_MAX_EVIDENCE_ITEMS", "10")),
            max_evidence_chars=int(os.getenv("AI_NAV_AGENT_MAX_EVIDENCE_CHARS", "12000")),
            allowed_hosts=_env_csv("AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS"),
            live_enabled=_env_bool("AI_NAV_AGENT_PROVIDER_LIVE_ENABLED"),
            upgrade_model=os.getenv(
                "AI_NAV_AGENT_PROVIDER_UPGRADE_MODEL",
                AGENT_STAGE1_UPGRADE_MODEL,
            ).strip(),
            upgrade_ratio=float(os.getenv("AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO", "0")),
            per_user_concurrency=int(os.getenv("AI_NAV_AGENT_PER_USER_CONCURRENCY", "1")),
            global_concurrency=int(os.getenv("AI_NAV_AGENT_GLOBAL_CONCURRENCY", "8")),
            queue_limit=int(os.getenv("AI_NAV_AGENT_QUEUE_LIMIT", "32")),
            queue_timeout_seconds=float(os.getenv("AI_NAV_AGENT_QUEUE_TIMEOUT_SECONDS", "3")),
            max_input_tokens=int(os.getenv("AI_NAV_AGENT_PROVIDER_MAX_INPUT_TOKENS", "4000")),
            input_cny_per_million=float(os.getenv("AI_NAV_AGENT_INPUT_CNY_PER_MILLION", "0.2")),
            output_cny_per_million=float(os.getenv("AI_NAV_AGENT_OUTPUT_CNY_PER_MILLION", "2.0")),
            per_request_cost_cny=float(os.getenv("AI_NAV_AGENT_PER_REQUEST_COST_CNY", "0.02")),
            per_user_daily_cost_cny=float(os.getenv("AI_NAV_AGENT_PER_USER_DAILY_COST_CNY", "0.1")),
            global_daily_cost_cny=float(os.getenv("AI_NAV_AGENT_GLOBAL_DAILY_COST_CNY", "5")),
            global_monthly_cost_cny=float(os.getenv("AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY", "80")),
        )
    except ValueError as exc:
        raise RuntimeError("Agent Provider numeric configuration is invalid") from exc
    validate_agent_provider_config(
        environment or APP_ENV,
        settings.provider,
        settings.base_url,
        settings.model,
        settings.api_key,
        settings.timeout_seconds,
        settings.max_retries,
        settings.max_output_tokens,
        settings.max_output_chars,
        settings.max_evidence_items,
        settings.max_evidence_chars,
        settings.allowed_hosts,
        settings.live_enabled,
        settings.upgrade_model,
        settings.upgrade_ratio,
        settings.per_user_concurrency,
        settings.global_concurrency,
        settings.queue_limit,
        settings.queue_timeout_seconds,
        settings.max_input_tokens,
        settings.input_cny_per_million,
        settings.output_cny_per_million,
        settings.per_request_cost_cny,
        settings.per_user_daily_cost_cny,
        settings.global_daily_cost_cny,
        settings.global_monthly_cost_cny,
    )
    return settings


DATABASE_PATH = Path(os.getenv("AI_NAV_DATABASE_PATH", str(BASE_DIR / "database" / "ai_nav.sqlite3"))).expanduser().resolve()
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"
LEARNING_CONTENT_PATH = BASE_DIR / "database" / "learning_content.sql"
MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = Path(os.getenv("AI_NAV_UPLOAD_DIR", str(BASE_DIR / "uploads"))).expanduser().resolve()

API_PREFIX = "/api/v1"
APP_NAME = "AI Knowledge Navigation API"
APP_ENV = os.getenv("AI_NAV_ENV", "development").strip().lower()
PUBLIC_BASE_PATH = normalize_public_base_path(os.getenv("AI_NAV_PUBLIC_BASE_PATH", ""))
HTTP_TEST_ACCOUNT_USERNAME = os.getenv("AI_NAV_HTTP_TEST_ACCOUNT_USERNAME", "").strip()
HTTP_TEST_GUEST_AGENT_ENABLED = _env_bool("AI_NAV_HTTP_TEST_GUEST_AGENT_ENABLED", "0")
APP_HOST = os.getenv("AI_NAV_APP_HOST", "127.0.0.1").strip()
APP_PORT = int(
    os.getenv(
        "AI_NAV_APP_PORT",
        "8001" if APP_ENV == "http_test" else "8002" if APP_ENV == "provider_preview" else "8088",
    )
)
HTTPS_CONFIRMED = _env_bool("AI_NAV_HTTPS_CONFIRMED", "0")
API_WORKERS = int(
    os.getenv(
        "AI_NAV_API_WORKERS",
        os.getenv("WEB_CONCURRENCY", "1"),
    )
)
AGENT_RUNTIME_STATE_BACKEND = os.getenv(
    "AI_NAV_AGENT_RUNTIME_STATE_BACKEND",
    "process_local",
).strip().lower()


def validate_agent_runtime_topology(
    declared_workers: int,
    state_backend: str,
) -> None:
    if not 1 <= declared_workers <= 64:
        raise RuntimeError("AI_NAV_API_WORKERS must be between 1 and 64")
    if state_backend != "process_local":
        raise RuntimeError(
            "AI_NAV_AGENT_RUNTIME_STATE_BACKEND is not implemented"
        )
    if declared_workers != 1:
        raise RuntimeError(
            "Agent process-local governance, replay, and metrics require "
            "AI_NAV_API_WORKERS=1 until a shared state backend is implemented"
        )


validate_agent_runtime_topology(API_WORKERS, AGENT_RUNTIME_STATE_BACKEND)
AGENT_STREAM_ENABLED = _env_bool("AI_NAV_AGENT_STREAM_ENABLED", "0")
AGENT_STREAM_BUFFER_EVENTS = int(
    os.getenv("AI_NAV_AGENT_STREAM_BUFFER_EVENTS", "8")
)
if not 1 <= AGENT_STREAM_BUFFER_EVENTS <= 64:
    raise RuntimeError("AI_NAV_AGENT_STREAM_BUFFER_EVENTS must be between 1 and 64")
AGENT_RESPONSE_REPLAY_TTL_SECONDS = int(
    os.getenv("AI_NAV_AGENT_RESPONSE_REPLAY_TTL_SECONDS", "300")
)
if not 30 <= AGENT_RESPONSE_REPLAY_TTL_SECONDS <= 900:
    raise RuntimeError(
        "AI_NAV_AGENT_RESPONSE_REPLAY_TTL_SECONDS must be between 30 and 900"
    )
AGENT_RESPONSE_REPLAY_MAX_ENTRIES = int(
    os.getenv("AI_NAV_AGENT_RESPONSE_REPLAY_MAX_ENTRIES", "512")
)
if not 16 <= AGENT_RESPONSE_REPLAY_MAX_ENTRIES <= 4096:
    raise RuntimeError(
        "AI_NAV_AGENT_RESPONSE_REPLAY_MAX_ENTRIES must be between 16 and 4096"
    )
AGENT_SESSIONS_ENABLED = _env_bool("AI_NAV_AGENT_SESSIONS_ENABLED", "0")
AGENT_SESSION_RETENTION_DAYS = int(
    os.getenv("AI_NAV_AGENT_SESSION_RETENTION_DAYS", "30")
)
if not 1 <= AGENT_SESSION_RETENTION_DAYS <= 90:
    raise RuntimeError("AI_NAV_AGENT_SESSION_RETENTION_DAYS must be between 1 and 90")
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
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
PASSWORD_HASH_ROUNDS = int(os.getenv("AI_NAV_PASSWORD_HASH_ROUNDS", "180000"))
ACCOUNT_DELETION_GRACE_DAYS = int(os.getenv("AI_NAV_ACCOUNT_DELETION_GRACE_DAYS", "7"))
ACCOUNT_DELETION_RETENTION_DAYS = int(os.getenv("AI_NAV_ACCOUNT_DELETION_RETENTION_DAYS", "30"))
PRIVACY_POLICY_VERSION = os.getenv("AI_NAV_PRIVACY_POLICY_VERSION", "2026-07-20")
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
AVATAR_MAX_REQUEST_BYTES = int(
    os.getenv("AVATAR_MAX_REQUEST_BYTES", str(AVATAR_MAX_UPLOAD_BYTES + 64 * 1024))
)
AVATAR_MAX_FRAMES = int(os.getenv("AVATAR_MAX_FRAMES", "1"))
AVATAR_PROCESSING_TIMEOUT_SECONDS = float(
    os.getenv("AVATAR_PROCESSING_TIMEOUT_SECONDS", "2.0")
)
validate_runtime_security(
    APP_ENV,
    SECRET_KEY,
    CORS_ALLOW_ORIGINS,
    REFRESH_COOKIE_SECURE,
    public_base_path=PUBLIC_BASE_PATH,
    http_test_account_username=HTTP_TEST_ACCOUNT_USERNAME,
    agent_provider=os.getenv("AI_NAV_AGENT_PROVIDER", "deterministic").strip().lower(),
    agent_provider_live_enabled=_env_bool("AI_NAV_AGENT_PROVIDER_LIVE_ENABLED"),
    app_host=APP_HOST,
    app_port=APP_PORT,
    reset_database_on_start=RESET_DATABASE_ON_START,
    database_path=DATABASE_PATH,
    upload_dir=UPLOAD_DIR,
    trusted_proxy_cidrs=TRUSTED_PROXY_CIDRS,
    refresh_cookie_samesite=REFRESH_COOKIE_SAMESITE,
    account_deletion_grace_days=ACCOUNT_DELETION_GRACE_DAYS,
    account_deletion_retention_days=ACCOUNT_DELETION_RETENTION_DAYS,
    avatar_max_request_bytes=AVATAR_MAX_REQUEST_BYTES,
    avatar_max_frames=AVATAR_MAX_FRAMES,
    avatar_processing_timeout_seconds=AVATAR_PROCESSING_TIMEOUT_SECONDS,
)
if APP_ENV in {"production", "provider_preview"}:
    get_agent_provider_settings(APP_ENV)
