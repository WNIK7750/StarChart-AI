from functools import lru_cache

from app.users.authorization.ports import AuthorizationRepository
from app.users.authorization.policy import authorization_context
from app.users.authorization.repositories.sqlite import SQLiteAuthorizationRepository
from app.users.common import UsersError


class AuthorizationService:
    def __init__(self, repository: AuthorizationRepository):
        self.repository = repository

    def user_context(self, user_id: int) -> dict:
        context = authorization_context(
            self.repository.list_role_codes(user_id),
            self.repository.list_permission_codes(user_id),
        )
        return {"roles": sorted(context.roles), "permissions": sorted(context.permissions)}

    def require_permission(self, user_id: int, permission: str) -> dict:
        context = self.user_context(user_id)
        if permission not in context["permissions"]:
            raise UsersError("PERMISSION_DENIED", "当前账号没有执行此操作的权限", 403)
        return context


@lru_cache(maxsize=1)
def get_authorization_service() -> AuthorizationService:
    return AuthorizationService(SQLiteAuthorizationRepository())
