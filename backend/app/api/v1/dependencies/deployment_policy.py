from collections.abc import Callable

from fastapi import HTTPException, Request

from app.users.common import users_error_detail
from app.users.deployment_policy import (
    DeploymentAction,
    DeploymentPolicyError,
    enforce_deployment_action,
)


def require_deployment_action(action: DeploymentAction) -> Callable:
    async def dependency(request: Request) -> None:
        login_identifier = None
        if action == "login":
            try:
                payload = await request.json()
            except (RuntimeError, ValueError):
                payload = None
            if isinstance(payload, dict) and isinstance(payload.get("identifier"), str):
                login_identifier = payload["identifier"]
        try:
            enforce_deployment_action(
                action,
                login_identifier=login_identifier,
            )
        except DeploymentPolicyError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=users_error_detail(exc),
            ) from exc

    return dependency
