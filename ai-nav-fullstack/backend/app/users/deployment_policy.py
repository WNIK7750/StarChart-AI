from hmac import compare_digest
from typing import Literal

from app.core.config import APP_ENV, HTTP_TEST_ACCOUNT_USERNAME
from app.users.account.identity import normalize_login_identifier
from app.users.account.service import normalize_username
from app.users.common import UsersError


DeploymentAction = Literal[
    "register",
    "login",
    "identity_update",
    "password_update",
    "recovery",
    "security_questions_update",
    "privacy_consent_update",
    "privacy_export",
    "account_deletion_request",
    "account_deletion_cancel",
]

RESTRICTED_CODE = "DEMO_ACCOUNT_RESTRICTED"
RESTRICTED_MESSAGE = "当前 HTTP 测试账号不允许执行此操作。"


class DeploymentPolicyError(UsersError):
    def __init__(self):
        super().__init__(RESTRICTED_CODE, RESTRICTED_MESSAGE, 403)


def _configured_username() -> str:
    try:
        return normalize_username(HTTP_TEST_ACCOUNT_USERNAME)
    except UsersError as exc:
        raise DeploymentPolicyError() from exc


def _presented_identifier(value: str | None) -> str:
    try:
        return normalize_login_identifier(value or "")
    except UsersError as exc:
        raise DeploymentPolicyError() from exc


def enforce_deployment_action(
    action: DeploymentAction,
    *,
    login_identifier: str | None = None,
) -> None:
    if APP_ENV != "http_test":
        return
    if action == "login":
        configured = _configured_username()
        presented = _presented_identifier(login_identifier)
        if compare_digest(
            presented.encode("utf-8"),
            configured.encode("utf-8"),
        ):
            return
    raise DeploymentPolicyError()
