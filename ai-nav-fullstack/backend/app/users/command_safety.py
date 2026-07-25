from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSafetySpec:
    domain: str
    audit: str
    replay: str
    concurrency: str


def _spec(domain: str, audit: str, replay: str, concurrency: str) -> CommandSafetySpec:
    return CommandSafetySpec(domain, audit, replay, concurrency)


# Every Users-owned HTTP command must be listed here. Controls are intentionally
# semantic: a one-time reset token is safer than bolting an idempotency key onto it.
COMMAND_SAFETY: dict[tuple[str, str], CommandSafetySpec] = {
    ("POST", "/api/v1/agent/workflows/save"): _spec("assets", "users.assets.workflow_created", "idempotency-key", "transaction+unique-key"),
    ("POST", "/api/v1/users/me/assets/workflows"): _spec("assets", "users.assets.workflow_created", "idempotency-key", "transaction+unique-key"),
    ("PATCH", "/api/v1/users/me/assets/workflows/{workflow_uid}"): _spec("assets", "users.assets.workflow_updated", "optimistic-version", "conditional-update"),
    ("POST", "/api/v1/users/me/assets/workflows/{workflow_uid}/archive"): _spec("assets", "users.assets.workflow_archived", "state-transition", "optimistic-version"),
    ("POST", "/api/v1/users/me/assets/workflows/{workflow_uid}/restore"): _spec("assets", "users.assets.workflow_restored", "state-transition", "optimistic-version"),
    ("POST", "/api/v1/auth/register"): _spec("authentication", "users.auth.registered", "unique-account-identity", "transaction+unique-constraint"),
    ("POST", "/api/v1/auth/login"): _spec("authentication", "users.auth.login_succeeded+users.privacy.consent_updated+login-log", "rate-limit", "atomic-lockout+session-insert"),
    ("POST", "/api/v1/auth/password-reset/start"): _spec("authentication", "users.auth.password_reset_started", "rate-limit+opaque-response", "transaction+sender-port"),
    ("POST", "/api/v1/auth/password-reset/confirm"): _spec("authentication", "users.auth.password_reset_completed", "single-use-token", "transactional-consume+session-revoke"),
    ("POST", "/api/v1/auth/password-reset/security/start"): _spec("authentication", "users.auth.password_reset_started", "deprecated-alias+rate-limit", "transaction+sender-port"),
    ("POST", "/api/v1/auth/password-reset/security/verify"): _spec("authentication", "users.auth.password_reset_verified", "disabled-410", "none"),
    ("POST", "/api/v1/auth/password-reset/security/confirm"): _spec("authentication", "users.auth.password_reset_completed", "deprecated-alias+single-use-token", "transactional-consume+session-revoke"),
    ("POST", "/api/v1/auth/refresh"): _spec("authentication", "users.auth.session_refreshed", "refresh-rotation+replay-detection", "transactional-rotation"),
    ("POST", "/api/v1/auth/logout"): _spec("authentication", "users.auth.session_logged_out", "natural-idempotency", "conditional-revoke"),
    ("PUT", "/api/v1/users/me/privacy/consents/{consent_type}"): _spec("privacy", "users.privacy.consent_updated", "append-only-event", "transaction+policy-version"),
    ("POST", "/api/v1/users/me/privacy/export"): _spec("privacy", "users.privacy.data_exported", "reauthenticated-request", "transaction"),
    ("POST", "/api/v1/users/me/privacy/deletion-requests"): _spec("privacy", "users.privacy.deletion_requested", "one-active-request", "transaction+unique-state"),
    ("DELETE", "/api/v1/users/me/privacy/deletion-requests/{request_uid}"): _spec("privacy", "users.privacy.deletion_cancelled", "state-transition", "conditional-update"),
    ("POST", "/api/v1/users/privacy/deletion-requests/{request_uid}/execute"): _spec("privacy", "users.privacy.deletion_executed", "state-transition", "transaction+conditional-state"),
    ("POST", "/api/v1/users/privacy/deletion-requests/{request_uid}/restore"): _spec("privacy", "users.privacy.deletion_restored", "state-transition", "transaction+conditional-state"),
    ("POST", "/api/v1/users/privacy/deletion-requests/{request_uid}/anonymize"): _spec("privacy", "users.privacy.deletion_anonymized", "terminal-state", "transaction+conditional-state"),
    ("PUT", "/api/v1/users/me/learning/nodes/{node_slug}/sections/{section_uid}"): _spec("learning_state", "learning.section_progress.updated", "optimistic-version", "transaction+version-check"),
    ("PUT", "/api/v1/users/me/learning/progress/{node_slug}"): _spec("learning_state", "learning.progress.updated", "optimistic-version", "transaction+version-check"),
    ("POST", "/api/v1/users/me/learning/activity"): _spec("learning_state", "learning.activity.recorded", "idempotency-key", "unique-key"),
    ("POST", "/api/v1/users/me/learning/import"): _spec("learning_state", "learning.activity.recorded", "content-derived-idempotency-key", "transaction+unique-key"),
    ("POST", "/api/v1/users/me/favorites"): _spec("learning_state", "learning.favorite.added", "natural-idempotency", "unique-target"),
    ("DELETE", "/api/v1/users/me/favorites/{favorite_uid}"): _spec("learning_state", "learning.favorite.removed", "resource-state", "owned-conditional-delete"),
    ("PATCH", "/api/v1/users/me/account"): _spec("account", "users.account.updated", "current-password-for-contact-change+natural-idempotency", "transaction+unique-constraint"),
    ("PATCH", "/api/v1/users/me/password"): _spec("security", "users.security.password_updated", "current-password-reauth", "transaction+token-version+session-revoke"),
    ("PUT", "/api/v1/users/me/security-questions"): _spec("security", "users.security.questions_replaced", "replace-semantics+reauth", "transaction"),
    ("PATCH", "/api/v1/users/me/profile"): _spec("profile", "users.profile.updated", "optimistic-version", "conditional-update"),
    ("POST", "/api/v1/users/me/avatar"): _spec("profile", "users.profile.avatar_updated", "content-replacement", "atomic-file-write+db-rollback"),
    ("PATCH", "/api/v1/users/me/preferences"): _spec("preferences", "users.preferences.updated", "optimistic-version", "conditional-update"),
    ("POST", "/api/v1/users/me/sessions/revoke-others"): _spec("sessions", "users.sessions.others_revoked", "natural-idempotency", "conditional-revoke"),
    ("DELETE", "/api/v1/users/me/sessions/{session_uid}"): _spec("sessions", "users.session.revoked", "natural-idempotency", "owned-conditional-revoke"),
}
