from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEventSpec:
    resource_type: str
    allowed_metadata: frozenset[str]


AUDIT_EVENTS: dict[str, AuditEventSpec] = {
    "users.auth.registered": AuditEventSpec("account", frozenset({"sessionIssued"})),
    "users.auth.login_succeeded": AuditEventSpec("session", frozenset({"sessionIssued"})),
    "users.auth.password_reset_started": AuditEventSpec("password_reset", frozenset({"stage"})),
    "users.auth.password_reset_verified": AuditEventSpec("password_reset", frozenset({"stage"})),
    "users.auth.password_reset_completed": AuditEventSpec(
        "password_reset",
        frozenset({"stage", "sessionsRevoked"}),
    ),
    "users.auth.session_refreshed": AuditEventSpec("session", frozenset({"rotation"})),
    "users.auth.session_logged_out": AuditEventSpec("session", frozenset({"scope"})),
    "users.account.updated": AuditEventSpec("account", frozenset({"changedFields"})),
    "users.security.password_updated": AuditEventSpec("security", frozenset({"sessionsRevoked"})),
    "users.security.questions_replaced": AuditEventSpec("security_questions", frozenset({"questionCount"})),
    "users.profile.updated": AuditEventSpec("profile", frozenset({"changedFields"})),
    "users.profile.avatar_updated": AuditEventSpec(
        "avatar",
        frozenset({"format", "storedBytes", "oldAvatarRemoved"}),
    ),
    "users.preferences.updated": AuditEventSpec("preferences", frozenset({"changedFields"})),
    "users.session.revoked": AuditEventSpec("session", frozenset({"scope"})),
    "users.sessions.others_revoked": AuditEventSpec("session", frozenset({"scope", "revokedCount"})),
    "users.privacy.consent_updated": AuditEventSpec(
        "privacy_consent",
        frozenset({"consentType", "policyVersion", "status"}),
    ),
    "users.privacy.data_exported": AuditEventSpec(
        "data_export",
        frozenset({"formatVersion"}),
    ),
    "users.privacy.deletion_requested": AuditEventSpec(
        "deletion_request",
        frozenset({"reasonCode", "scheduledFor"}),
    ),
    "users.privacy.deletion_cancelled": AuditEventSpec("deletion_request", frozenset()),
    "users.privacy.deletion_executed": AuditEventSpec(
        "deletion_request",
        frozenset({"retentionUntil"}),
    ),
    "users.privacy.deletion_restored": AuditEventSpec("deletion_request", frozenset()),
    "users.privacy.deletion_anonymized": AuditEventSpec("deletion_request", frozenset()),
    "users.assets.workflow_created": AuditEventSpec(
        "saved_workflow",
        frozenset({"sourceType", "stepCount"}),
    ),
    "users.assets.workflow_updated": AuditEventSpec(
        "saved_workflow",
        frozenset({"changedFields", "version"}),
    ),
    "users.assets.workflow_archived": AuditEventSpec(
        "saved_workflow",
        frozenset({"version"}),
    ),
    "users.assets.workflow_restored": AuditEventSpec(
        "saved_workflow",
        frozenset({"version"}),
    ),
}
