from typing import Protocol


class AuthorizationRepository(Protocol):
    def list_role_codes(self, user_id: int) -> list[str]: ...

    def list_permission_codes(self, user_id: int) -> list[str]: ...
