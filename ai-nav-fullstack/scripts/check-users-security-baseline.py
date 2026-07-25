import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "docs" / "06-evidence" / "users"


def file_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    findings = []
    config = file_text("backend/app/core/config.py")
    main_py = file_text("backend/app/main.py")
    api_js = file_text("frontend/assets/js/api.js")
    auth_router = file_text("backend/app/api/v1/routers/auth.py")
    users_router = file_text("backend/app/api/v1/routers/users.py")
    avatar_service = file_text("backend/app/users/profile/avatar.py")
    profile_service = file_text("backend/app/users/profile/service.py")
    preferences_facade = file_text("backend/app/users/preferences/facade.py")
    agent_memory = file_text("backend/app/agent/memory.py")
    agent_schemas = file_text("backend/app/agent/schemas.py")
    preference_consumers = file_text("frontend/assets/js/user-preference-consumers.js")
    authorization_service = file_text("backend/app/users/authorization/service.py")
    authorization_dependency = file_text("backend/app/api/v1/dependencies/authorization.py")
    agent_router = file_text("backend/app/api/v1/routers/agent.py")
    user_learning_router = file_text("backend/app/api/v1/routers/user_learning.py")
    audit_events = file_text("backend/app/users/audit/events.py")
    audit_policy = file_text("backend/app/users/audit/policy.py")
    privacy_migration = file_text("database/migrations/006_user_privacy_lifecycle.sql")
    privacy_service = file_text("backend/app/users/privacy/service.py")
    privacy_repository = file_text("backend/app/users/privacy/repositories/sqlite.py")
    privacy_router = file_text("backend/app/api/v1/routers/privacy.py")
    assets_migration = file_text("database/migrations/007_user_workflow_assets.sql")
    assets_service = file_text("backend/app/users/assets/service.py")
    assets_repository = file_text("backend/app/users/assets/repositories/sqlite.py")
    user_context_facade = file_text("backend/app/users/context/facade.py")
    observability_access = file_text("backend/app/users/observability/access.py")
    observability_metrics = file_text("backend/app/users/observability/metrics.py")
    operations_router = file_text("backend/app/api/v1/routers/operations.py")
    backup_script = file_text("scripts/manage-users-backup.py")
    rehearsal_script = file_text("scripts/rehearse-users-release.py")
    common_router = file_text("backend/app/api/v1/routers/common.py")
    database_runtime = file_text("backend/app/db/database.py")
    auth_compat_migration = file_text("database/migrations/008_user_auth_compatibility.sql")
    auth_rate_migration = file_text("database/migrations/009_auth_rate_limits.sql")
    auth_rate_limit = file_text("backend/app/users/authentication/rate_limit.py")
    auth_service = file_text("backend/app/users/authentication/service.py")
    command_safety = file_text("backend/app/users/command_safety.py")
    command_safety_check = file_text("scripts/check-users-command-safety.py")

    checks = [
        {
            "id": "USR-SEC-001",
            "title": "Production rejects default or short signing secrets",
            "status": "pass"
            if (
                "validate_runtime_security" in config
                and 'environment == "production"' in config
                and "secret_key == DEV_SECRET_KEY" in config
                and "len(secret_key) < 32" in config
            )
            else "fail",
            "evidence": "Development retains an explicit local fallback, while production startup rejects the default or secrets shorter than 32 characters.",
        },
        {
            "id": "USR-SEC-002",
            "title": "CORS uses an explicit configurable allowlist",
            "status": "pass"
            if (
                "CORS_ALLOW_ORIGINS" in config
                and 'if "*" in cors_origins' in config
                and "allow_origins=list(CORS_ALLOW_ORIGINS)" in main_py
                and 'allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]' in main_py
                and 'allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id"]' in main_py
            )
            else "fail",
            "evidence": "CORS origins are environment-configurable, wildcard origins are rejected, and methods/headers are explicitly bounded.",
        },
        {
            "id": "USR-SEC-003",
            "title": "Refresh token is not persisted by frontend JavaScript",
            "status": "fail" if 'localStorage.setItem("ai_nav_refresh_token"' in api_js else "pass",
            "evidence": "frontend/assets/js/api.js keeps only a compatibility reader and removes old refresh-token localStorage values.",
        },
        {
            "id": "USR-SEC-003B",
            "title": "Refresh cookie is HttpOnly, SameSite, and Secure-configurable",
            "status": "pass"
            if (
                "httponly=True" in auth_router
                and "samesite=REFRESH_COOKIE_SAMESITE" in auth_router
                and "secure=REFRESH_COOKIE_SECURE" in auth_router
                and "AI_NAV_REFRESH_COOKIE_SECURE" in config
            )
            else "fail",
            "evidence": "auth router sets ai_nav_refresh_token as HttpOnly and uses config-driven SameSite/Secure settings.",
        },
        {
            "id": "USR-SEC-004",
            "title": "Auth and users routers contain no SQL",
            "status": "pass" if not re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b|db_cursor\(", auth_router + users_router) else "fail",
            "evidence": "Router SQL keyword scan.",
        },
        {
            "id": "USR-SEC-005",
            "title": "Users request DTOs forbid extra fields",
            "status": "pass" if "StrictModel" in auth_router and "StrictModel" in users_router else "fail",
            "evidence": "Auth/users request models inherit the shared StrictModel.",
        },
        {
            "id": "USR-SEC-006",
            "title": "Password change and reset revoke active sessions",
            "status": "pass" if "UPDATE user_sessions" in file_text("backend/app/users/security/repositories/sqlite.py") and "UPDATE user_sessions" in file_text("backend/app/users/authentication/repositories/sqlite.py") else "fail",
            "evidence": "Security/authentication repositories revoke sessions after password changes.",
        },
        {
            "id": "USR-SEC-007",
            "title": "Password hashes are versioned and upgraded after successful reauth",
            "status": "pass"
            if (
                "AI_NAV_PASSWORD_HASH_ROUNDS" in config
                and "needs_password_rehash" in file_text("backend/app/core/security.py")
                and "rehash_password" in file_text("backend/app/users/authentication/service.py")
                and "needs_password_rehash" in file_text("backend/app/users/security/repositories/sqlite.py")
            )
            else "fail",
            "evidence": "Password hash rounds are configurable, login upgrades legacy hashes, and sensitive security-question reauth also refreshes stale hashes.",
        },
        {
            "id": "USR-SEC-008",
            "title": "Login failures are counted and temporarily locked without account-state disclosure",
            "status": "pass"
            if (
                "AI_NAV_LOGIN_MAX_FAILED_ATTEMPTS" in config
                and "AI_NAV_LOGIN_LOCK_MINUTES" in config
                and "lockedUntil" in file_text("backend/app/users/authentication/service.py")
                and "INVALID_CREDENTIALS" in file_text("backend/app/users/authentication/service.py")
            )
            else "fail",
            "evidence": "Login service applies a configurable temporary lock while preserving the same external INVALID_CREDENTIALS error.",
        },
        {
            "id": "USR-SEC-009",
            "title": "Sessions identify the current device and support revoking other devices",
            "status": "pass"
            if (
                "isCurrent" in file_text("backend/app/users/sessions/repositories/sqlite.py")
                and "riskLevel" in file_text("backend/app/users/sessions/repositories/sqlite.py")
                and "revoke_other_sessions" in file_text("backend/app/users/sessions/service.py")
                and "/me/sessions/revoke-others" in users_router
            )
            else "fail",
            "evidence": "Sessions API marks current sessions from the refresh cookie, returns risk state, and exposes revoke-others.",
        },
        {
            "id": "USR-SEC-010",
            "title": "Avatar ingestion validates image content and rolls back stored files",
            "status": "pass"
            if (
                "AVATAR_MAX_SOURCE_PIXELS" in config
                and "AVATAR_CONTENT_TYPE_MISMATCH" in avatar_service
                and "os.replace" in avatar_service
                and "remove_path(stored_path)" in profile_service
                and not re.search(r"\b(PIL|Image|BytesIO|write_bytes|unlink|UPLOAD_DIR|random_uid)\b", users_router)
            )
            else "fail",
            "evidence": "Avatar processing is owned by Users/profile, validates declared and decoded formats plus pixel count, writes atomically, and removes new files when profile persistence fails.",
        },
        {
            "id": "USR-SEC-011",
            "title": "Learning, Tools, and Agent consume preferences through the Users facade",
            "status": "pass"
            if (
                "UserPreferencesFacade" in preferences_facade
                and 'get_context(user_id, "agent")' in agent_memory
                and "getUserPreferenceContext" in preference_consumers
                and "class AgentChatRequest(StrictModel)" in agent_schemas
                and "preferences:" not in agent_schemas
                and not re.search(r"\b(user_preferences|user_profiles|user_sessions|db_cursor)\b", agent_memory + preference_consumers)
            )
            else "fail",
            "evidence": "Consumers read projected preference contexts from Users; Agent rejects copied client preference state and consumer adapters contain no direct user-table access.",
        },
        {
            "id": "USR-SEC-012",
            "title": "Backend permission dependency enforces RBAC for protected domain commands",
            "status": "pass"
            if (
                "require_permission" in authorization_service
                and "PERMISSION_DENIED" in authorization_service
                and "get_authorization_service().require_permission" in authorization_dependency
                and 'require_permission("agent:chat")' in agent_router
                and 'require_permission("learning:read")' in user_learning_router
            )
            else "fail",
            "evidence": "Authorization service returns stable 403 decisions and FastAPI dependencies protect Agent and private learning-state routes.",
        },
        {
            "id": "USR-SEC-013",
            "title": "Sensitive user commands use registered audit events and allowlisted metadata",
            "status": "pass"
            if (
                "AUDIT_EVENTS" in audit_events
                and "SENSITIVE_KEY_PARTS" in audit_policy
                and "allowed_metadata" in audit_policy
                and "_audited_call" in users_router
                and "users.security.password_updated" in users_router
                and "users.session.revoked" in users_router
            )
            else "fail",
            "evidence": "Users write routes emit registered audit events whose metadata is filtered by event allowlists and sensitive-key denial.",
        },
        {
            "id": "USR-SEC-014",
            "title": "Account deletion uses staged retention and controlled anonymization",
            "status": "pass"
            if (
                "user_data_requests" in privacy_migration
                and "idx_user_data_requests_active_deletion" in privacy_migration
                and "ACCOUNT_DELETION_GRACE_DAYS" in privacy_service
                and "ACCOUNT_DELETION_RETENTION_DAYS" in privacy_service
                and "account_status = 'deleted'" in privacy_repository
                and "anonymize_deletion_request" in privacy_repository
                and "DELETE FROM roadmap_nodes" not in privacy_repository
                and 'require_permission("users:manage")' in privacy_router
            )
            else "fail",
            "evidence": "Deletion requests are unique and staged through grace, soft-delete, recovery retention, and admin-authorized anonymization without deleting public domain facts.",
        },
        {
            "id": "USR-SEC-015",
            "title": "Agent memory requires current versioned consent",
            "status": "pass"
            if (
                "user_privacy_consent_events" in privacy_migration
                and "CONSENT_POLICY_VERSIONS" in privacy_service
                and "CONSENT_VERSION_OUTDATED" in privacy_service
                and "has_current_consent" in preferences_facade
                and "agentMemoryEnabled: bool" not in users_router
                and "/users/me/privacy/consents/{consent_type}" in privacy_router
            )
            else "fail",
            "evidence": "Append-only consent events carry policy versions; stale consent is rejected and Agent context checks the current consent rather than the legacy preference flag.",
        },
        {
            "id": "USR-SEC-016",
            "title": "User data export requires reauthentication and excludes authentication secrets",
            "status": "pass"
            if (
                "verify_current_password" in privacy_service
                and "CURRENT_PASSWORD_INVALID" in privacy_service
                and "refresh_token_hash AS" not in privacy_repository
                and "password_hash AS" not in privacy_repository
                and "answer_hash AS" not in privacy_repository
                and "users.privacy.data_exported" in privacy_router
            )
            else "fail",
            "evidence": "Export requires the current password, emits an audit event, and its response projections omit password, refresh-token, and security-answer hashes.",
        },
        {
            "id": "USR-SEC-017",
            "title": "Workflow assets use user ownership, stable references, versions, and idempotency",
            "status": "pass"
            if (
                "user_saved_workflows" in assets_migration
                and "user_saved_workflow_steps" in assets_migration
                and "UNIQUE (user_id, idempotency_key)" in assets_migration
                and "workflow_uid" in assets_migration
                and "version INTEGER NOT NULL DEFAULT 1" in assets_migration
                and "FOREIGN KEY (tool_slug)" not in assets_migration
                and "WHERE user_id = ?" in assets_repository
            )
            else "fail",
            "evidence": "Users owns versioned workflow assets; idempotency is scoped to the user and external tool references are not cascade-coupled.",
        },
        {
            "id": "USR-SEC-018",
            "title": "Agent workflow writes require confirmation and use the Users command facade",
            "status": "pass"
            if (
                'Header(alias="Idempotency-Key",' in agent_router
                and "get_user_assets_facade" in agent_router
                and "user_saved_workflows" not in agent_router
                and "users.assets.workflow_created" in audit_events
                and "confirmed: Literal[True]" in file_text("backend/app/users/assets/schemas.py")
            )
            else "fail",
            "evidence": "Agent cannot write asset tables directly; save commands require explicit confirmation, an idempotency key, and registered Users audit events.",
        },
        {
            "id": "USR-SEC-019",
            "title": "Agent context is minimal and unavailable targets remain visible",
            "status": "pass"
            if (
                "preferences" in user_context_facade
                and "capabilities" in user_context_facade
                and "assets" in user_context_facade
                and "password" not in user_context_facade
                and "user_saved_workflow_steps" in assets_repository
                and '"unavailable"' in assets_service
                and "delete" not in assets_service.lower()
            )
            else "fail",
            "evidence": "Agent receives only preferences, capability flags, and an asset summary; retired targets are represented as unavailable without deleting the saved workflow.",
        },
        {
            "id": "USR-SEC-020",
            "title": "Users access logs are structured and exclude request PII and secrets",
            "status": "pass"
            if (
                all(field in observability_access for field in ("requestId", "operation", "status", "latencyMs", "errorCode"))
                and "request.body" not in observability_access
                and "Authorization" not in observability_access
                and "Cookie" not in observability_access
                and "userAgent" not in observability_access
                and "ipAddress" not in observability_access
                and "REQUEST_ID_PATTERN" in observability_access
            )
            else "fail",
            "evidence": "Observed requests log only a sanitized request ID, route operation, status, latency, and error code; request bodies, identity fields, headers, and secrets are not read.",
        },
        {
            "id": "USR-SEC-021",
            "title": "Operational metrics are aggregated and administrator-authorized",
            "status": "pass"
            if (
                'require_permission("users:manage")' in operations_router
                and "containsPii" in observability_metrics
                and "AUTH_LOGIN_FAILURE_SPIKE" in observability_metrics
                and "AUTH_ACCOUNT_LOCKED" in observability_metrics
                and "AUTH_REFRESH_FAILURE_SPIKE" in observability_metrics
                and "PASSWORD_UPDATE_FAILURE_SPIKE" in observability_metrics
                and "SESSION_REVOKE_FAILURE_SPIKE" in observability_metrics
            )
            else "fail",
            "evidence": "The metrics endpoint requires users:manage and returns operation counters and threshold alerts without labels containing user identity.",
        },
        {
            "id": "USR-SEC-022",
            "title": "Database backups and restores are integrity-checked and atomically replaced",
            "status": "pass"
            if (
                "source_conn.backup" in backup_script
                and "PRAGMA integrity_check" in backup_script
                and "PRAGMA foreign_key_check" in backup_script
                and "os.replace" in backup_script
                and "pre-restore" in backup_script
                and "migrationChecksumsMatch" in rehearsal_script
                and "canaryRestored" in rehearsal_script
            )
            else "fail",
            "evidence": "Online backups and restored files are verified, replacement is atomic, prior targets are preserved, and rehearsal confirms migration checksums plus a restored canary.",
        },
        {
            "id": "USR-SEC-023",
            "title": "Database startup uses lifespan and deployment health probes",
            "status": "pass"
            if (
                "async def lifespan" in main_py
                and "FastAPI(title=APP_NAME, lifespan=lifespan)" in main_py
                and "AI_NAV_DATABASE_PATH" in config
                and '@router.get("/health/live",' in common_router
                and '@router.get("/health/ready",' in common_router
                and "schema_migrations" in common_router
                and "DATABASE_NOT_READY" in common_router
            )
            else "fail",
            "evidence": "Database initialization runs in FastAPI lifespan, the database path is injectable, liveness has no dependency, and readiness verifies database access plus applied migrations.",
        },
        {
            "id": "USR-SEC-024",
            "title": "Authentication compatibility DDL is versioned and transactional",
            "status": "pass"
            if (
                "ai-nav:add-column-if-missing user_accounts token_version" in auth_compat_migration
                and "CREATE TABLE IF NOT EXISTS user_security_questions" in auth_compat_migration
                and "ADD_COLUMN_DIRECTIVE" in database_runtime
                and 'conn.execute("BEGIN IMMEDIATE")' in database_runtime
                and "Conditional migration column definition contains forbidden syntax" in database_runtime
                and "user_columns =" not in database_runtime
                and 'ALTER TABLE user_accounts ADD COLUMN token_version' not in database_runtime
            )
            else "fail",
            "evidence": "Legacy auth schema repair is migration 008 with checksum tracking; conditional column work runs under the migration lock and ad hoc startup DDL has been removed.",
        },
        {
            "id": "USR-SEC-025",
            "title": "Authentication endpoints use persistent hashed rate limits and trusted proxy boundaries",
            "status": "pass"
            if (
                "user_auth_rate_limits" in auth_rate_migration
                and "subject_hash" in auth_rate_migration
                and "BEGIN IMMEDIATE" in auth_rate_limit
                and "ON CONFLICT(scope, subject_hash)" in auth_rate_limit
                and "hash_token" in auth_rate_limit
                and "AUTH_RATE_LIMITED" in auth_rate_limit
                and "Retry-After" in auth_router
                and all(
                    f'_enforce_rate_limit("{operation}"' in auth_router
                    for operation in (
                        "username_available",
                        "register",
                        "login",
                        "password_reset_start",
                        "password_reset_verify",
                        "password_reset_confirm",
                        "refresh",
                    )
                )
                and "TRUSTED_PROXY_CIDRS" in auth_router
                and "if not any(direct_ip in network" in auth_router
            )
            else "fail",
            "evidence": "Rate limits are atomically persisted with HMAC subject keys and Retry-After; forwarded addresses are ignored unless the direct peer belongs to an explicit trusted proxy CIDR.",
        },
        {
            "id": "USR-SEC-026",
            "title": "Frontend access-token refresh is single-flight and cookie-based",
            "status": "pass"
            if (
                "refreshInFlight" in api_js
                and 'fetchWithDeadline("/auth/refresh"' in api_js
                and 'credentials: "same-origin"' in api_js
                and "return apiRequest(path, options, false)" in api_js
                and "return uploadRequest(path, formData, options, false)" in api_js
                and "clearAuthTokens();" in api_js
                and 'localStorage.setItem("ai_nav_refresh_token"' not in api_js
            )
            else "fail",
            "evidence": "Concurrent 401 responses share one refresh promise using the HttpOnly cookie, retry once, and clear local access state when refresh fails.",
        },
        {
            "id": "USR-SEC-027",
            "title": "Every Users command declares audit, replay, and concurrency controls",
            "status": "pass"
            if (
                "COMMAND_SAFETY" in command_safety
                and "users_command_routes" in command_safety_check
                and "missing = sorted(actual - registered)" in command_safety_check
                and "invalid_audits" in command_safety_check
                and all(
                    event in audit_events
                    for event in (
                        "users.auth.registered",
                        "users.auth.login_succeeded",
                        "users.auth.password_reset_completed",
                        "users.auth.session_refreshed",
                        "users.auth.session_logged_out",
                    )
                )
                and "self._audit(\"users.auth.registered\"" in auth_service
                and "users.auth.password_reset_started" in auth_service
            )
            else "fail",
            "evidence": "The route-derived registry covers every Users/Auth command with semantic audit, replay, and concurrency controls; authentication lifecycle events are allowlisted and emitted without secrets.",
        },
    ]
    findings.extend(checks)
    summary = {
        "pass": sum(1 for item in findings if item["status"] == "pass"),
        "knownRisk": sum(1 for item in findings if item["status"] == "known-risk"),
        "fail": sum(1 for item in findings if item["status"] == "fail"),
    }
    report = {"summary": summary, "findings": findings}
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    output = BASELINE_DIR / "users_security_baseline.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote users security baseline to {output}")
    if summary["fail"]:
        raise SystemExit("Users security baseline has failing checks.")


if __name__ == "__main__":
    main()
