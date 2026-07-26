import sqlite3
from collections.abc import Callable
from contextlib import contextmanager
from sqlite3 import Connection
from typing import Iterator

from app.db.database import get_connection


class SQLiteAuthenticationRepository:
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
    def _public_user(row: dict) -> dict:
        return {
            "id": row["id"],
            "user_uid": row["user_uid"],
            "username": row["username"],
            "email": row["email"],
            "phone": row["phone"],
            "account_status": row["account_status"],
            "token_version": row["token_version"],
            "email_verified": row["email_verified"],
            "phone_verified": row["phone_verified"],
            "last_login_at": row["last_login_at"],
            "created_at": row["created_at"],
        }

    def is_username_available(self, username: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM user_accounts WHERE lower(username) = lower(?) AND deleted_at IS NULL",
                (username,),
            ).fetchone()
            return row is None

    def register_user(self, item: dict) -> dict:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO user_accounts(user_uid, username, email, phone, account_status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (item["userUid"], item["username"], item["email"], item["phone"]),
                )
                user_id = cursor.lastrowid
                conn.execute(
                    "INSERT INTO user_auth_passwords(user_id, password_hash) VALUES (?, ?)",
                    (user_id, item["passwordHash"]),
                )
                conn.execute(
                    "INSERT INTO user_profiles(user_id, display_name) VALUES (?, ?)",
                    (user_id, item["displayName"]),
                )
                conn.execute("INSERT INTO user_preferences(user_id) VALUES (?)", (user_id,))
                conn.execute(
                    """
                    INSERT INTO user_privacy_consent_events(
                        event_uid, user_id, consent_type, policy_version, action, source
                    ) VALUES (?, ?, 'privacy_policy', ?, 'granted', 'registration')
                    """,
                    (item["privacyConsentEventUid"], user_id, item["privacyPolicyVersion"]),
                )
                conn.execute(
                    "INSERT INTO user_role_assignments(user_id, role_id) SELECT ?, id FROM roles WHERE code = 'user'",
                    (user_id,),
                )
                user = conn.execute(
                    """
                    SELECT id, user_uid, username, email, phone, account_status, token_version,
                           email_verified, phone_verified, last_login_at, created_at
                    FROM user_accounts WHERE id = ?
                    """,
                    (user_id,),
                ).fetchone()
                return self._public_user(user)
            except sqlite3.IntegrityError:
                raise

    def has_current_privacy_consent(self, user_id: int, policy_version: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT action, policy_version
                FROM user_privacy_consent_events
                WHERE user_id = ? AND consent_type = 'privacy_policy'
                ORDER BY id DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            return bool(row and row["action"] == "granted" and row["policy_version"] == policy_version)

    def find_login_user(self, identifier: str) -> dict | None:
        lookup = identifier.lower() if "@" in identifier else identifier
        with self._connect() as conn:
            user = conn.execute(
                """
                SELECT account.id, account.user_uid, account.username, account.email, account.phone,
                       account.account_status, account.token_version, account.email_verified,
                       account.phone_verified, account.last_login_at, account.created_at,
                       consent.action AS privacyConsentAction,
                       consent.policy_version AS privacyConsentPolicyVersion
                FROM user_accounts account
                LEFT JOIN user_privacy_consent_events consent ON consent.id = (
                    SELECT current.id FROM user_privacy_consent_events current
                    WHERE current.user_id = account.id AND current.consent_type = 'privacy_policy'
                    ORDER BY current.id DESC LIMIT 1
                )
                WHERE (account.username = ? OR lower(account.email) = lower(?) OR account.phone = ?) AND account.deleted_at IS NULL
                """,
                (identifier, lookup, identifier),
            ).fetchone()
            if not user:
                return None
            password = conn.execute(
                """
                SELECT password_hash, failed_attempts AS failedAttempts, locked_until AS lockedUntil
                FROM user_auth_passwords
                WHERE user_id = ?
                """,
                (user["id"],),
            ).fetchone()
            return {
                **self._public_user(user),
                "password_hash": password["password_hash"] if password else None,
                "failedAttempts": int(password["failedAttempts"] if password else 0),
                "lockedUntil": password["lockedUntil"] if password else None,
                "privacyConsentAction": user["privacyConsentAction"],
                "privacyConsentPolicyVersion": user["privacyConsentPolicyVersion"],
            }

    def rehash_password(self, user_id: int, password_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_auth_passwords
                SET password_hash = ?, password_algo = 'pbkdf2_sha256',
                    password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (password_hash, user_id),
            )

    def record_login(self, user_id: int | None, identifier: str, ok: bool, failure_reason: str | None, ip_address: str, user_agent: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_login_logs(user_id, login_identifier, result, failure_reason, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, identifier, "success" if ok else "failed", failure_reason, ip_address, user_agent),
            )

    def increment_failed_attempts(self, user_id: int, max_attempts: int, locked_until: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_auth_passwords
                SET failed_attempts = failed_attempts + 1,
                    locked_until = CASE WHEN failed_attempts + 1 >= ? THEN ? ELSE locked_until END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (max_attempts, locked_until, user_id),
            )

    def mark_login_success(self, user_id: int, ip_address: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_accounts
                SET last_login_at = CURRENT_TIMESTAMP, last_login_ip = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (ip_address, user_id),
            )
            conn.execute(
                "UPDATE user_auth_passwords SET failed_attempts = 0, locked_until = NULL, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,),
            )

    def create_session(self, item: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_sessions(
                  session_uid, user_id, refresh_token_hash, device_name, user_agent,
                  ip_address, expires_at, last_seen_at, token_family_uid, parent_session_id,
                  is_persistent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                """,
                (
                    item["sessionUid"],
                    item["userId"],
                    item["refreshTokenHash"],
                    item["deviceName"],
                    item["userAgent"],
                    item["ipAddress"],
                    item["expiresAt"],
                    item.get("tokenFamilyUid") or item["sessionUid"],
                    item.get("parentSessionId"),
                    int(bool(item.get("isPersistent", False))),
                ),
            )

    def get_current_user_by_uid(self, user_uid: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, user_uid, username, email, phone, account_status, token_version,
                       email_verified, phone_verified, last_login_at, created_at
                FROM user_accounts
                WHERE user_uid = ? AND deleted_at IS NULL
                """,
                (user_uid,),
            ).fetchone()
            return self._public_user(row) if row else None

    def get_token_version(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT token_version FROM user_accounts WHERE id = ?", (user_id,)).fetchone()
            return int(row["token_version"] if row else 0)

    def find_refresh_session(self, refresh_token_hash: str) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT s.id, s.user_id AS userId, u.user_uid AS userUid,
                       u.username AS username,
                       u.account_status AS accountStatus, u.token_version AS tokenVersion,
                        s.session_uid AS sessionUid,
                        COALESCE(s.token_family_uid, s.session_uid) AS tokenFamilyUid,
                        s.device_name AS deviceName, s.expires_at AS expiresAt,
                        s.is_persistent AS isPersistent
                FROM user_sessions s
                JOIN user_accounts u ON u.id = s.user_id
                WHERE s.refresh_token_hash = ? AND s.is_revoked = 0 AND s.expires_at > CURRENT_TIMESTAMP
                """,
                (refresh_token_hash,),
            ).fetchone()

    def find_any_refresh_session(self, refresh_token_hash: str) -> dict | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT s.id, s.user_id AS userId, u.user_uid AS userUid,
                       u.username AS username,
                       u.account_status AS accountStatus, u.token_version AS tokenVersion,
                       s.session_uid AS sessionUid,
                       COALESCE(s.token_family_uid, s.session_uid) AS tokenFamilyUid,
                       s.is_revoked AS isRevoked, s.revoked_reason AS revokedReason,
                       s.expires_at AS expiresAt
                FROM user_sessions s
                JOIN user_accounts u ON u.id = s.user_id
                WHERE s.refresh_token_hash = ?
                """,
                (refresh_token_hash,),
            ).fetchone()

    def touch_session(self, session_id: int, ip_address: str, user_agent: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_sessions SET last_seen_at = CURRENT_TIMESTAMP, ip_address = ?, user_agent = ? WHERE id = ?",
                (ip_address, user_agent, session_id),
            )

    def rotate_refresh_session(self, session_id: int, item: dict) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                """
                SELECT id, user_id AS userId, session_uid AS sessionUid,
                       COALESCE(token_family_uid, session_uid) AS tokenFamilyUid
                FROM user_sessions
                WHERE id = ? AND is_revoked = 0 AND expires_at > CURRENT_TIMESTAMP
                """,
                (session_id,),
            ).fetchone()
            if not current:
                raise sqlite3.IntegrityError("REFRESH_SESSION_NOT_ACTIVE")
            cursor = conn.execute(
                """
                INSERT INTO user_sessions(
                  session_uid, user_id, refresh_token_hash, device_name, user_agent,
                  ip_address, expires_at, last_seen_at, token_family_uid, parent_session_id,
                  is_persistent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                """,
                (
                    item["sessionUid"],
                    current["userId"],
                    item["refreshTokenHash"],
                    item["deviceName"],
                    item["userAgent"],
                    item["ipAddress"],
                    item["expiresAt"],
                    current["tokenFamilyUid"],
                    current["id"],
                    int(bool(item.get("isPersistent", False))),
                ),
            )
            conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP,
                    revoked_reason = 'rotated', replaced_by_session_id = ?
                WHERE id = ?
                """,
                (cursor.lastrowid, current["id"]),
            )

    def revoke_token_family(self, user_id: int, token_family_uid: str, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = ?
                WHERE user_id = ? AND COALESCE(token_family_uid, session_uid) = ? AND is_revoked = 0
                """,
                (reason, user_id, token_family_uid),
            )

    def revoke_refresh_token(self, user_id: int, refresh_token_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = 'logout'
                WHERE user_id = ? AND refresh_token_hash = ?
                """,
                (user_id, refresh_token_hash),
            )

    def create_password_recovery(
        self,
        identifier: str,
        token_uid: str,
        token_hash: str,
        expires_at: str,
    ) -> dict | None:
        lookup = identifier.lower() if "@" in identifier else identifier
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            user = conn.execute(
                """
                SELECT id, user_uid AS userUid, username, email, phone, account_status,
                       email_verified AS emailVerified, phone_verified AS phoneVerified
                FROM user_accounts
                WHERE (username = ? OR lower(email) = lower(?) OR phone = ?) AND deleted_at IS NULL
                """,
                (identifier, lookup, identifier),
            ).fetchone()
            if user and user["account_status"] == "active" and user["email"] and user["emailVerified"]:
                channel = "email"
                target = user["email"]
            elif user and user["account_status"] == "active" and user["phone"] and user["phoneVerified"]:
                channel = "sms"
                target = user["phone"]
            else:
                channel = None
                target = None
            conn.execute(
                """
                INSERT INTO user_verification_tokens(token_uid, user_id, target, purpose, token_hash, expires_at)
                VALUES (?, ?, ?, 'password_reset', ?, ?)
                """,
                (
                    token_uid,
                    user["id"] if channel else None,
                    f"recovery:{channel}:{target}" if channel else "recovery:discard",
                    token_hash,
                    expires_at,
                ),
            )
            if not channel:
                return None
            return {
                "id": user["id"],
                "userUid": user["userUid"],
                "recoveryChannel": channel,
                "recoveryTarget": target,
            }

    def cancel_password_recovery(self, token_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_verification_tokens
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE token_hash = ? AND purpose = 'password_reset' AND consumed_at IS NULL
                """,
                (token_hash,),
            )

    def confirm_security_reset(self, reset_token_hash: str, password_hash: str) -> dict | None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            token = conn.execute(
                """
                SELECT token.token_uid AS tokenUid, token.user_id AS userId,
                       account.user_uid AS userUid
                FROM user_verification_tokens token
                JOIN user_accounts account ON account.id = token.user_id
                WHERE token.token_hash = ? AND token.purpose = 'password_reset'
                  AND token.target LIKE 'recovery:%'
                  AND token.consumed_at IS NULL AND token.expires_at > CURRENT_TIMESTAMP
                """,
                (reset_token_hash,),
            ).fetchone()
            if not token:
                return None
            conn.execute(
                """
                UPDATE user_auth_passwords
                SET password_hash = ?, failed_attempts = 0, locked_until = NULL,
                    password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (password_hash, token["userId"]),
            )
            conn.execute(
                "UPDATE user_accounts SET token_version = token_version + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (token["userId"],),
            )
            conn.execute(
                """
                UPDATE user_sessions
                SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP, revoked_reason = 'password_reset'
                WHERE user_id = ? AND is_revoked = 0
                """,
                (token["userId"],),
            )
            conn.execute(
                "UPDATE user_verification_tokens SET consumed_at = CURRENT_TIMESTAMP WHERE token_uid = ?",
                (token["tokenUid"],),
            )
            return token
