from collections.abc import Callable

from fastapi import Depends, HTTPException

from app.api.v1.routers.auth import get_current_user
from app.users.authorization.service import get_authorization_service
from app.users.common import UsersError, users_error_detail


def require_permission(permission: str) -> Callable:
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        try:
            context = get_authorization_service().require_permission(current_user["id"], permission)
        except UsersError as exc:
            raise HTTPException(status_code=exc.status_code, detail=users_error_detail(exc)) from exc
        return {**current_user, **context}

    return dependency
