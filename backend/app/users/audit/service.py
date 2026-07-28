from functools import lru_cache
from typing import Any

from app.users.audit.events import AUDIT_EVENTS
from app.users.audit.policy import sanitize_audit_metadata
from app.users.audit.ports import AuditRepository
from app.users.audit.repositories.sqlite import SQLiteAuditRepository
from app.users.common import UsersError


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def record(
        self,
        event: str,
        *,
        actor_user_id: int | None,
        target_user_id: int | None,
        resource_id: str | None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        spec = AUDIT_EVENTS.get(event)
        if not spec:
            raise UsersError("AUDIT_EVENT_UNKNOWN", "审计事件未注册", 500)
        return self.repository.append(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action=event,
            resource_type=spec.resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=sanitize_audit_metadata(spec, metadata),
        )


@lru_cache(maxsize=1)
def get_audit_service() -> AuditService:
    return AuditService(SQLiteAuditRepository())
