from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationContext:
    roles: frozenset[str]
    permissions: frozenset[str]

    def allows(self, permission: str) -> bool:
        return permission in self.permissions


def authorization_context(roles: list[str] | set[str], permissions: list[str] | set[str]) -> AuthorizationContext:
    return AuthorizationContext(
        roles=frozenset(str(role) for role in roles),
        permissions=frozenset(str(permission) for permission in permissions),
    )


def role_codes(user: dict) -> set[str]:
    return {str(role) for role in (user.get("roles") or [])}


def permission_codes(user: dict) -> set[str]:
    return {str(permission) for permission in (user.get("permissions") or [])}


def has_permission(user: dict, permission: str) -> bool:
    return permission in permission_codes(user)
