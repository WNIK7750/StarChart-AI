from datetime import timedelta
from functools import lru_cache

from app.core.config import (
    ACCOUNT_DELETION_GRACE_DAYS,
    ACCOUNT_DELETION_RETENTION_DAYS,
    AGENT_MEMORY_POLICY_VERSION,
    PRIVACY_POLICY_VERSION,
)
from app.core.security import iso_datetime, random_uid, utc_now
from app.users.common import UsersError
from app.users.privacy.ports import PrivacyRepository
from app.users.privacy.repositories.sqlite import SQLitePrivacyRepository
from app.users.profile.avatar import AvatarStorage


CONSENT_POLICY_VERSIONS = {
    "privacy_policy": PRIVACY_POLICY_VERSION,
    "agent_memory": AGENT_MEMORY_POLICY_VERSION,
}
DELETION_REASON_CODES = {"privacy", "unused", "other"}


class PrivacyService:
    def __init__(self, repository: PrivacyRepository, avatar_storage: AvatarStorage | None = None):
        self.repository = repository
        self.avatar_storage = avatar_storage or AvatarStorage()

    def consent_status(self, user_id: int) -> dict:
        current = {item["consentType"]: item for item in self.repository.list_current_consents(user_id)}
        items = []
        for consent_type, expected_version in CONSENT_POLICY_VERSIONS.items():
            recorded = current.get(consent_type)
            granted = bool(
                recorded
                and recorded["action"] == "granted"
                and recorded["policyVersion"] == expected_version
            )
            items.append(
                {
                    "consentType": consent_type,
                    "policyVersion": expected_version,
                    "status": "granted" if granted else "revoked",
                    "recordedPolicyVersion": recorded["policyVersion"] if recorded else None,
                    "recordedAt": recorded["createdAt"] if recorded else None,
                    "source": recorded["source"] if recorded else None,
                }
            )
        return {"items": items, "meta": {"source": "users.privacy", "contractVersion": 1}}

    def has_current_consent(self, user_id: int, consent_type: str) -> bool:
        if consent_type not in CONSENT_POLICY_VERSIONS:
            return False
        status = self.consent_status(user_id)
        return any(item["consentType"] == consent_type and item["status"] == "granted" for item in status["items"])

    def set_consent(
        self,
        user_id: int,
        consent_type: str,
        policy_version: str,
        granted: bool,
        source: str = "settings",
    ) -> dict:
        expected_version = CONSENT_POLICY_VERSIONS.get(consent_type)
        if not expected_version:
            raise UsersError("CONSENT_TYPE_INVALID", "不支持的同意类型", 422)
        if policy_version != expected_version:
            raise UsersError("CONSENT_VERSION_OUTDATED", "同意版本已更新，请重新确认", 409)
        event = self.repository.append_consent(
            random_uid("cons"),
            user_id,
            consent_type,
            policy_version,
            "granted" if granted else "revoked",
            source,
        )
        return {
            "consent": {
                "consentType": consent_type,
                "policyVersion": policy_version,
                "status": "granted" if granted else "revoked",
                "recordedAt": event["createdAt"],
                "source": source,
            }
        }

    def export_user_data(self, user_id: int, current_password: str) -> dict:
        if not self.repository.verify_current_password(user_id, current_password):
            raise UsersError("CURRENT_PASSWORD_INVALID", "当前密码不正确", 401)
        request = self.repository.create_export_request(random_uid("datareq"), user_id)
        return {
            "request": request,
            "export": {
                "format": "application/json",
                "formatVersion": 1,
                "generatedAt": iso_datetime(utc_now()),
                "data": self.repository.export_user_data(user_id),
            },
        }

    def current_deletion_request(self, user_id: int) -> dict:
        return {"request": self.repository.current_deletion_request(user_id)}

    def request_deletion(self, user_id: int, current_password: str, reason_code: str) -> dict:
        if reason_code not in DELETION_REASON_CODES:
            raise UsersError("DELETION_REASON_INVALID", "注销原因无效", 422)
        if not self.repository.verify_current_password(user_id, current_password):
            raise UsersError("CURRENT_PASSWORD_INVALID", "当前密码不正确", 401)
        scheduled_for = iso_datetime(utc_now() + timedelta(days=ACCOUNT_DELETION_GRACE_DAYS))
        request = self.repository.create_deletion_request(
            random_uid("datareq"),
            user_id,
            reason_code,
            scheduled_for,
        )
        if not request:
            raise UsersError("DELETION_REQUEST_EXISTS", "已有进行中的账号注销申请", 409)
        return {"request": request}

    def cancel_deletion(self, user_id: int, request_uid: str) -> dict:
        request = self.repository.cancel_deletion_request(user_id, request_uid)
        if not request:
            raise UsersError("DELETION_REQUEST_NOT_CANCELLABLE", "注销申请不存在或当前无法取消", 404)
        return {"request": request}

    def execute_deletion(self, request_uid: str) -> dict:
        now = utc_now()
        result = self.repository.execute_deletion_request(
            request_uid,
            iso_datetime(now),
            iso_datetime(now + timedelta(days=ACCOUNT_DELETION_RETENTION_DAYS)),
        )
        if not result:
            raise UsersError("DELETION_REQUEST_NOT_DUE", "注销申请不存在、尚未到期或状态无效", 409)
        return result

    def restore_deletion(self, request_uid: str) -> dict:
        result = self.repository.restore_deletion_request(request_uid, iso_datetime(utc_now()))
        if not result:
            raise UsersError("DELETION_RESTORE_UNAVAILABLE", "账号不在可恢复保留期内", 409)
        return result

    def anonymize_deletion(self, request_uid: str) -> dict:
        result = self.repository.anonymize_deletion_request(request_uid, iso_datetime(utc_now()))
        if not result:
            raise UsersError("DELETION_RETENTION_ACTIVE", "账号仍在恢复保留期内或状态无效", 409)
        self.avatar_storage.remove_managed_url(result.get("avatarUrl"))
        return result


@lru_cache(maxsize=1)
def get_privacy_service() -> PrivacyService:
    return PrivacyService(SQLitePrivacyRepository())
