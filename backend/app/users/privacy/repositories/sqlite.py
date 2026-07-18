from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.core.security import verify_password
from app.db.database import get_connection


class SQLitePrivacyRepository:
    def __init__(self, connection_factory: Callable[[], Connection] = get_connection):
        self._connection_factory = connection_factory

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        conn = self._connection_factory()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _request(row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "requestUid": row["request_uid"],
            "requestType": row["request_type"],
            "status": row["status"],
            "reasonCode": row["reason_code"],
            "scheduledFor": row["scheduled_for"],
            "retentionUntil": row["retention_until"],
            "completedAt": row["completed_at"],
            "cancelledAt": row["cancelled_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def verify_current_password(self, user_id: int, password: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT password_hash FROM user_auth_passwords WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return bool(row and verify_password(password, row["password_hash"]))

    def list_current_consents(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT event_uid AS eventUid, consent_type AS consentType,
                       policy_version AS policyVersion, action, source, created_at AS createdAt
                FROM user_privacy_consent_events event
                WHERE user_id = ?
                  AND id = (
                    SELECT MAX(current.id)
                    FROM user_privacy_consent_events current
                    WHERE current.user_id = event.user_id
                      AND current.consent_type = event.consent_type
                  )
                ORDER BY consent_type
                """,
                (user_id,),
            ).fetchall()

    def append_consent(self, event_uid: str, user_id: int, consent_type: str, policy_version: str, action: str, source: str) -> dict:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_privacy_consent_events(
                    event_uid, user_id, consent_type, policy_version, action, source
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_uid, user_id, consent_type, policy_version, action, source),
            )
            return conn.execute(
                """
                SELECT event_uid AS eventUid, consent_type AS consentType,
                       policy_version AS policyVersion, action, source, created_at AS createdAt
                FROM user_privacy_consent_events WHERE event_uid = ?
                """,
                (event_uid,),
            ).fetchone()

    def create_export_request(self, request_uid: str, user_id: int) -> dict:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_data_requests(
                    request_uid, user_id, request_type, status, completed_at
                ) VALUES (?, ?, 'export', 'completed', CURRENT_TIMESTAMP)
                """,
                (request_uid, user_id),
            )
            row = conn.execute("SELECT * FROM user_data_requests WHERE request_uid = ?", (request_uid,)).fetchone()
            return self._request(row)

    @staticmethod
    def _rows(conn: Connection, query: str, user_id: int) -> list[dict]:
        return conn.execute(query, (user_id,)).fetchall()

    def export_user_data(self, user_id: int) -> dict:
        with self._connect() as conn:
            account = conn.execute(
                """
                SELECT user_uid AS userUid, username, email, phone,
                       account_status AS accountStatus, email_verified AS emailVerified,
                       phone_verified AS phoneVerified, last_login_at AS lastLoginAt,
                       created_at AS createdAt, updated_at AS updatedAt
                FROM user_accounts WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
            profile = conn.execute(
                """
                SELECT display_name AS displayName, avatar_url AS avatarUrl, bio,
                       role_title AS roleTitle, learning_level AS learningLevel,
                       target_direction AS targetDirection, created_at AS createdAt,
                       updated_at AS updatedAt
                FROM user_profiles WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            preferences = conn.execute(
                """
                SELECT theme, language, cn_first AS cnFirst, free_first AS freeFirst,
                       show_external_resources AS showExternalResources,
                       created_at AS createdAt, updated_at AS updatedAt
                FROM user_preferences WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return {
                "account": account,
                "profile": profile,
                "preferences": preferences,
                "securityQuestions": self._rows(
                    conn,
                    "SELECT question_order AS questionOrder, question_text AS question, created_at AS createdAt FROM user_security_questions WHERE user_id = ? ORDER BY question_order",
                    user_id,
                ),
                "sessions": self._rows(
                    conn,
                    """
                    SELECT session_uid AS sessionUid, device_name AS deviceName,
                           country_region AS countryRegion, is_revoked AS isRevoked,
                           revoked_at AS revokedAt, expires_at AS expiresAt,
                           last_seen_at AS lastSeenAt, created_at AS createdAt
                    FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC
                    """,
                    user_id,
                ),
                "learningProgress": self._rows(
                    conn,
                    """
                    SELECT node_slug AS nodeSlug, status, progress_percent AS progressPercent,
                           started_at AS startedAt, completed_at AS completedAt,
                           last_studied_at AS lastStudiedAt, created_at AS createdAt,
                           updated_at AS updatedAt
                    FROM user_learning_progress WHERE user_id = ? ORDER BY node_slug
                    """,
                    user_id,
                ),
                "learningActivity": self._rows(
                    conn,
                    """
                    SELECT activity_uid AS activityUid, node_slug AS nodeSlug,
                           target_type AS targetType, target_key AS targetKey,
                           activity_type AS activityType, created_at AS createdAt
                    FROM user_learning_activity WHERE user_id = ? ORDER BY created_at DESC
                    """,
                    user_id,
                ),
                "favorites": self._rows(
                    conn,
                    """
                    SELECT favorite_uid AS favoriteUid, target_type AS targetType,
                           target_key AS targetKey, title_snapshot AS title,
                           description_snapshot AS description, created_at AS createdAt
                    FROM user_favorites WHERE user_id = ? ORDER BY created_at DESC
                    """,
                    user_id,
                ),
                "savedWorkflows": self._rows(
                    conn,
                    """
                    SELECT workflow_uid AS workflowUid, title, description,
                           source_type AS sourceType, source_ref AS sourceRef,
                           status, version, archived_at AS archivedAt,
                           created_at AS createdAt, updated_at AS updatedAt
                    FROM user_saved_workflows WHERE user_id = ? ORDER BY id
                    """,
                    user_id,
                ),
                "consentEvents": self._rows(
                    conn,
                    """
                    SELECT event_uid AS eventUid, consent_type AS consentType,
                           policy_version AS policyVersion, action, source,
                           created_at AS createdAt
                    FROM user_privacy_consent_events WHERE user_id = ? ORDER BY id
                    """,
                    user_id,
                ),
                "dataRequests": self._rows(
                    conn,
                    """
                    SELECT request_uid AS requestUid, request_type AS requestType,
                           status, reason_code AS reasonCode, scheduled_for AS scheduledFor,
                           retention_until AS retentionUntil, completed_at AS completedAt,
                           cancelled_at AS cancelledAt, created_at AS createdAt
                    FROM user_data_requests WHERE user_id = ? ORDER BY id
                    """,
                    user_id,
                ),
                "auditEvents": conn.execute(
                    """
                    SELECT action, resource_type AS resourceType, resource_id AS resourceId,
                           created_at AS createdAt
                    FROM user_audit_logs
                    WHERE actor_user_id = ? OR target_user_id = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (user_id, user_id),
                ).fetchall(),
            }

    def current_deletion_request(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM user_data_requests
                WHERE user_id = ? AND request_type = 'deletion'
                  AND status IN ('pending', 'processing')
                ORDER BY id DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            return self._request(row)

    def create_deletion_request(self, request_uid: str, user_id: int, reason_code: str, scheduled_for: str) -> dict:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT id FROM user_data_requests
                WHERE user_id = ? AND request_type = 'deletion'
                  AND status IN ('pending', 'processing')
                """,
                (user_id,),
            ).fetchone()
            if existing:
                return {}
            conn.execute(
                """
                INSERT INTO user_data_requests(
                    request_uid, user_id, request_type, status, reason_code, scheduled_for
                ) VALUES (?, ?, 'deletion', 'pending', ?, ?)
                """,
                (request_uid, user_id, reason_code, scheduled_for),
            )
            row = conn.execute("SELECT * FROM user_data_requests WHERE request_uid = ?", (request_uid,)).fetchone()
            return self._request(row) or {}

    def cancel_deletion_request(self, user_id: int, request_uid: str) -> dict | None:
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE user_data_requests
                SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE request_uid = ? AND user_id = ? AND request_type = 'deletion'
                  AND status = 'pending'
                """,
                (request_uid, user_id),
            )
            if not result.rowcount:
                return None
            return self._request(conn.execute("SELECT * FROM user_data_requests WHERE request_uid = ?", (request_uid,)).fetchone())

    def execute_deletion_request(self, request_uid: str, now: str, retention_until: str) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT request.*, account.user_uid
                FROM user_data_requests request
                JOIN user_accounts account ON account.id = request.user_id
                WHERE request.request_uid = ? AND request.request_type = 'deletion'
                  AND request.status = 'pending' AND request.scheduled_for <= ?
                """,
                (request_uid, now),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE user_accounts
                SET account_status = 'deleted', deleted_at = ?, token_version = token_version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (now, row["user_id"]),
            )
            conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = ?, revoked_reason = 'account_disabled'
                WHERE user_id = ? AND is_revoked = 0
                """,
                (now, row["user_id"]),
            )
            conn.execute(
                """
                UPDATE user_data_requests
                SET status = 'processing', retention_until = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (retention_until, row["id"]),
            )
            return {"userId": row["user_id"], "userUid": row["user_uid"], "request": self._request(conn.execute("SELECT * FROM user_data_requests WHERE id = ?", (row["id"],)).fetchone())}

    def restore_deletion_request(self, request_uid: str, now: str) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT request.*, account.user_uid
                FROM user_data_requests request
                JOIN user_accounts account ON account.id = request.user_id
                WHERE request.request_uid = ? AND request.request_type = 'deletion'
                  AND request.status = 'processing' AND request.retention_until > ?
                  AND account.account_status = 'deleted'
                """,
                (request_uid, now),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE user_accounts
                SET account_status = 'active', deleted_at = NULL,
                    token_version = token_version + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (row["user_id"],),
            )
            conn.execute(
                """
                UPDATE user_data_requests
                SET status = 'cancelled', cancelled_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (now, row["id"]),
            )
            return {"userId": row["user_id"], "userUid": row["user_uid"], "request": self._request(conn.execute("SELECT * FROM user_data_requests WHERE id = ?", (row["id"],)).fetchone())}

    def anonymize_deletion_request(self, request_uid: str, now: str) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT request.*, account.user_uid, profile.avatar_url
                FROM user_data_requests request
                JOIN user_accounts account ON account.id = request.user_id
                LEFT JOIN user_profiles profile ON profile.user_id = request.user_id
                WHERE request.request_uid = ? AND request.request_type = 'deletion'
                  AND request.status = 'processing' AND request.retention_until <= ?
                  AND account.account_status = 'deleted'
                """,
                (request_uid, now),
            ).fetchone()
            if not row:
                return None
            user_id = row["user_id"]
            conn.execute(
                """
                INSERT INTO user_privacy_consent_events(
                    event_uid, user_id, consent_type, policy_version, action, source
                )
                SELECT 'cons_' || lower(hex(randomblob(16))), latest.user_id,
                       latest.consent_type, latest.policy_version, 'revoked', 'admin'
                FROM user_privacy_consent_events latest
                WHERE latest.user_id = ? AND latest.action = 'granted'
                  AND latest.id = (
                    SELECT MAX(current.id)
                    FROM user_privacy_consent_events current
                    WHERE current.user_id = latest.user_id
                      AND current.consent_type = latest.consent_type
                  )
                """,
                (user_id,),
            )
            conn.execute(
                """
                DELETE FROM user_saved_workflow_steps
                WHERE workflow_id IN (
                    SELECT id FROM user_saved_workflows WHERE user_id = ?
                )
                """,
                (user_id,),
            )
            conn.execute("DELETE FROM user_saved_workflows WHERE user_id = ?", (user_id,))
            for table in (
                "user_learning_section_progress",
                "user_learning_progress",
                "user_learning_activity",
                "user_favorites",
                "user_sessions",
                "user_security_questions",
                "user_verification_tokens",
                "user_auth_passwords",
                "user_role_assignments",
            ):
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            conn.execute(
                """
                UPDATE user_profiles
                SET display_name = '已注销用户', avatar_url = NULL, bio = NULL,
                    role_title = NULL, target_direction = NULL, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )
            conn.execute(
                """
                UPDATE user_preferences
                SET theme = 'light', language = 'zh-CN', cn_first = 1, free_first = 0,
                    show_external_resources = 1, agent_memory_enabled = 0,
                    preference_json = NULL, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )
            conn.execute(
                """
                UPDATE user_login_logs
                SET login_identifier = 'deleted:' || ?, ip_address = NULL, user_agent = NULL
                WHERE user_id = ?
                """,
                (row["user_uid"], user_id),
            )
            conn.execute(
                """
                UPDATE user_audit_logs
                SET ip_address = NULL, user_agent = NULL, metadata_json = '{}'
                WHERE actor_user_id = ? OR target_user_id = ?
                """,
                (user_id, user_id),
            )
            conn.execute(
                """
                UPDATE user_accounts
                SET username = NULL, email = NULL, phone = NULL,
                    email_verified = 0, phone_verified = 0,
                    last_login_ip = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (user_id,),
            )
            conn.execute(
                """
                UPDATE user_data_requests
                SET status = 'completed', completed_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (now, row["id"]),
            )
            return {
                "userId": user_id,
                "userUid": row["user_uid"],
                "avatarUrl": row["avatar_url"],
                "request": self._request(conn.execute("SELECT * FROM user_data_requests WHERE id = ?", (row["id"],)).fetchone()),
            }
