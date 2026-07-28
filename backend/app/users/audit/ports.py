from typing import Protocol


class AuditRepository(Protocol):
    def append(
        self,
        *,
        actor_user_id: int | None,
        target_user_id: int | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        metadata: dict,
    ) -> int: ...
