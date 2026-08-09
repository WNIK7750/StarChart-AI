from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urlsplit

from app.core.config import AGENT_USER_MODEL_ALLOWED_HOSTS
from app.users.common import UsersError
from app.users.model_settings.credential_store import (
    CredentialStoreOperationError,
    CredentialStoreUnavailable,
    create_platform_credential_store,
)
from app.users.model_settings.ports import (
    AgentModelCredentialStore,
    AgentModelSettingsRepository,
)
from app.users.model_settings.repositories.sqlite import SQLiteAgentModelSettingsRepository


@dataclass(frozen=True, slots=True)
class ResolvedAgentModelSettings:
    provider_name: str
    base_url: str
    model_display_name: str
    model_id: str
    api_key: str
    max_output_tokens: int | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AgentModelSettingsService:
    def __init__(
        self,
        repository: AgentModelSettingsRepository,
        credential_store: AgentModelCredentialStore,
        allowed_hosts: tuple[str, ...] = AGENT_USER_MODEL_ALLOWED_HOSTS,
    ):
        self.repository = repository
        self.credential_store = credential_store
        self.allowed_hosts = tuple(host.lower() for host in allowed_hosts)

    def get_public(self, user_id: int, credential_subject: str) -> dict:
        row = self.repository.get(user_id)
        if not row:
            return {"model": self._public(None)}
        return {"model": self._public(row, has_api_key=self._get_secret(credential_subject) is not None)}

    def save(self, user_id: int, credential_subject: str, values: dict) -> dict:
        current = self.repository.get(user_id)
        base_url = self._validate_base_url(values["baseUrl"])
        api_key = (values.get("apiKey") or "").strip()
        previous_secret = self._get_secret(credential_subject)
        if not api_key and previous_secret is None:
            raise UsersError("AGENT_MODEL_API_KEY_REQUIRED", "首次配置必须填写 API 密钥", 422)
        changed_connection = bool(
            not current
            or base_url != current["baseUrl"]
            or values["modelId"].strip() != current["modelId"]
            or api_key
        )
        token_limit = values.get("maxOutputTokens")
        payload = {
            "providerKey": values.get("providerKey", "custom").strip(),
            "providerName": values["providerName"].strip(),
            "baseUrl": base_url,
            "modelDisplayName": values["modelDisplayName"].strip(),
            "modelId": values["modelId"].strip(),
            "maxOutputTokens": int(token_limit) if token_limit is not None else None,
            "enabled": bool(values["enabled"]),
            "connectionStatus": "needs_retest" if changed_connection else current["connectionStatus"],
            "connectionErrorCode": None if changed_connection else current.get("connectionErrorCode"),
            "connectionCheckedAt": None if changed_connection else current.get("connectionCheckedAt"),
        }
        if api_key:
            self._put_secret(credential_subject, api_key)
        try:
            row, updated = self.repository.upsert(
                user_id,
                payload,
                values.get("expectedVersion"),
            )
        except Exception:
            if api_key:
                self._restore_secret(credential_subject, previous_secret)
            raise
        if not updated:
            if api_key:
                self._restore_secret(credential_subject, previous_secret)
            raise UsersError(
                "AGENT_MODEL_VERSION_CONFLICT",
                "模型配置已在其他位置更新，请刷新后重试",
                409,
            )
        return {"model": self._public(row, has_api_key=True)}

    def resolve(self, user_id: int, credential_subject: str) -> ResolvedAgentModelSettings | None:
        row = self.repository.get(user_id)
        if not row or not row["enabled"]:
            return None
        api_key = self._get_secret(credential_subject)
        if api_key is None:
            raise UsersError(
                "AGENT_MODEL_CREDENTIAL_MISSING",
                "模型凭据不存在，请在设置中重新填写 API Key",
                409,
            )
        return ResolvedAgentModelSettings(
            provider_name=row["providerName"],
            base_url=row["baseUrl"],
            model_display_name=row["modelDisplayName"],
            model_id=row["modelId"],
            api_key=api_key,
            max_output_tokens=row["maxOutputTokens"],
        )

    def record_connection(self, user_id: int, *, ok: bool, error_code: str | None) -> dict:
        current = self.repository.get(user_id)
        if not current:
            raise UsersError("AGENT_MODEL_NOT_CONFIGURED", "请先保存模型配置", 404)
        checked_at = _utc_now()
        payload = {
            **current,
            "connectionStatus": "healthy" if ok else "error",
            "connectionErrorCode": error_code,
            "connectionCheckedAt": checked_at,
        }
        row, updated = self.repository.upsert(user_id, payload, current["version"])
        if not updated:
            raise UsersError("AGENT_MODEL_VERSION_CONFLICT", "模型配置已更新，请重试", 409)
        return {
            "ok": ok,
            "status": row["connectionStatus"],
            "errorCode": error_code,
            "message": "模型连接正常" if ok else "模型连接失败，请按错误代码检查配置",
            "checkedAt": checked_at,
        }

    def delete(self, user_id: int, credential_subject: str) -> None:
        previous_secret = self._get_secret(credential_subject)
        self._delete_secret(credential_subject)
        try:
            self.repository.delete(user_id)
        except Exception:
            if previous_secret is not None:
                self._put_secret(credential_subject, previous_secret)
            raise

    def _get_secret(self, subject: str) -> str | None:
        try:
            return self.credential_store.get(subject)
        except (CredentialStoreUnavailable, CredentialStoreOperationError) as exc:
            raise UsersError(
                "AGENT_MODEL_CREDENTIAL_STORE_UNAVAILABLE",
                "系统凭据存储暂不可用，请检查运行账号或凭据存储配置",
                503,
            ) from exc

    def _put_secret(self, subject: str, secret: str) -> None:
        try:
            self.credential_store.put(subject, secret)
        except (CredentialStoreUnavailable, CredentialStoreOperationError) as exc:
            raise UsersError(
                "AGENT_MODEL_CREDENTIAL_STORE_UNAVAILABLE",
                "API Key 未保存：系统凭据存储暂不可用",
                503,
            ) from exc

    def _delete_secret(self, subject: str) -> None:
        try:
            self.credential_store.delete(subject)
        except (CredentialStoreUnavailable, CredentialStoreOperationError) as exc:
            raise UsersError(
                "AGENT_MODEL_CREDENTIAL_STORE_UNAVAILABLE",
                "系统凭据存储暂不可用，未删除模型配置",
                503,
            ) from exc

    def _restore_secret(self, subject: str, previous_secret: str | None) -> None:
        if previous_secret is None:
            self._delete_secret(subject)
        else:
            self._put_secret(subject, previous_secret)

    def _validate_base_url(self, value: str) -> str:
        url = value.strip().rstrip("/")
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise UsersError(
                "AGENT_MODEL_BASE_URL_INVALID",
                "模型地址必须是无账号、查询参数和片段的 HTTPS 地址",
                422,
            )
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address and not address.is_global:
            raise UsersError("AGENT_MODEL_HOST_BLOCKED", "模型地址不能指向本机或私有网络", 422)
        if host not in self.allowed_hosts:
            raise UsersError(
                "AGENT_MODEL_HOST_NOT_ALLOWED",
                "该模型域名尚未由站点管理员加入允许列表",
                422,
            )
        return url

    def _public(self, row: dict | None, *, has_api_key: bool = False) -> dict:
        if not row:
            return {
                "configured": False,
                "maxOutputTokens": None,
                "enabled": False,
                "hasApiKey": False,
                "connectionStatus": "not_configured",
                "allowedHosts": list(self.allowed_hosts),
            }
        return {
            "configured": True,
            "providerKey": row["providerKey"],
            "providerName": row["providerName"],
            "baseUrl": row["baseUrl"],
            "modelDisplayName": row["modelDisplayName"],
            "modelId": row["modelId"],
            "maxOutputTokens": row["maxOutputTokens"],
            "enabled": row["enabled"],
            "hasApiKey": has_api_key,
            "connectionStatus": row["connectionStatus"],
            "connectionErrorCode": row.get("connectionErrorCode"),
            "connectionCheckedAt": row.get("connectionCheckedAt"),
            "version": row["version"],
            "allowedHosts": list(self.allowed_hosts),
        }


@lru_cache(maxsize=1)
def get_agent_model_settings_service() -> AgentModelSettingsService:
    return AgentModelSettingsService(
        SQLiteAgentModelSettingsRepository(),
        create_platform_credential_store(),
    )
