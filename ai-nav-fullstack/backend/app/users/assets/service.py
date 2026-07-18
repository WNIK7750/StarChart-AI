from functools import lru_cache
from typing import Any

from app.core.security import random_uid
from app.tools.service import get_tool_catalog
from app.users.assets.ports import AssetsRepository
from app.users.assets.repositories.sqlite import SQLiteAssetsRepository
from app.users.audit.service import AuditService, get_audit_service
from app.users.common import UsersError


class AssetsService:
    def __init__(self, repository: AssetsRepository, audit: AuditService | None = None):
        self.repository = repository
        self.audit = audit or get_audit_service()

    @staticmethod
    def _tool_map() -> dict[str, dict]:
        return {tool["id"]: tool for tool in get_tool_catalog()["tools"]}

    def _decorate(self, workflow: dict) -> dict:
        tools = self._tool_map()
        unavailable_count = 0
        steps = []
        for step in workflow["steps"]:
            tool_slug = step.get("toolSlug")
            tool = tools.get(tool_slug) if tool_slug else None
            if tool_slug and not tool:
                unavailable_count += 1
            steps.append(
                {
                    **step,
                    "target": (
                        {
                            "type": "tool",
                            "key": tool_slug,
                            "status": "available" if tool else "unavailable",
                            "name": tool["name"] if tool else step.get("toolNameSnapshot"),
                            "href": tool["href"] if tool else step.get("toolHrefSnapshot"),
                        }
                        if tool_slug
                        else None
                    ),
                }
            )
        return {
            **workflow,
            "steps": steps,
            "availability": {
                "status": "degraded" if unavailable_count else "available",
                "unavailableTargetCount": unavailable_count,
            },
        }

    def _audit(self, event: str, workflow: dict, context: dict, metadata: dict) -> None:
        self.audit.record(
            event,
            actor_user_id=context["actorUserId"],
            target_user_id=context["targetUserId"],
            resource_id=workflow["workflowUid"],
            metadata=metadata,
            ip_address=context.get("ipAddress"),
            user_agent=context.get("userAgent"),
        )

    def create_workflow(self, user_id: int, payload: dict, idempotency_key: str, context: dict) -> dict:
        orders = [step["order"] for step in payload["steps"]]
        if len(set(orders)) != len(orders):
            raise UsersError("WORKFLOW_STEP_ORDER_DUPLICATE", "工作流步骤顺序不能重复", 422)
        tools = self._tool_map()
        steps = []
        for step in sorted(payload["steps"], key=lambda item: item["order"]):
            tool = tools.get(step.get("toolSlug"))
            steps.append(
                {
                    **step,
                    "stepUid": random_uid("wfstep"),
                    "toolNameSnapshot": step.get("toolNameSnapshot") or (tool["name"] if tool else None),
                    "toolHrefSnapshot": step.get("toolHrefSnapshot") or (tool["href"] if tool else None),
                }
            )
        workflow, replayed = self.repository.create_workflow(
            user_id,
            random_uid("workflow"),
            idempotency_key,
            payload,
            steps,
        )
        decorated = self._decorate(workflow)
        if not replayed:
            self._audit(
                "users.assets.workflow_created",
                decorated,
                context,
                {"sourceType": payload["sourceType"], "stepCount": len(steps)},
            )
        return {"workflow": decorated, "meta": {"idempotencyReplayed": replayed, "contractVersion": 1}}

    def get_workflow(self, user_id: int, workflow_uid: str) -> dict:
        workflow = self.repository.get_workflow(user_id, workflow_uid)
        if not workflow:
            raise UsersError("WORKFLOW_NOT_FOUND", "工作流不存在", 404)
        return {"workflow": self._decorate(workflow)}

    def list_workflows(self, user_id: int, page: int = 1, page_size: int = 20, status: str = "active") -> dict:
        if status not in {"active", "archived", "all"}:
            raise UsersError("WORKFLOW_STATUS_INVALID", "工作流状态无效", 422)
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        total = self.repository.count_workflows(user_id, status)
        items = self.repository.list_workflows(user_id, status, page_size, (page - 1) * page_size)
        return {
            "items": [self._decorate(item) for item in items],
            "meta": {
                "page": page,
                "pageSize": page_size,
                "totalCount": total,
                "hasNext": page * page_size < total,
                "source": "users.assets",
                "contractVersion": 1,
            },
        }

    def update_workflow(self, user_id: int, workflow_uid: str, expected_version: int, values: dict, context: dict) -> dict:
        clean = {key: value.strip() if isinstance(value, str) else value for key, value in values.items() if value is not None}
        workflow, updated = self.repository.update_workflow(user_id, workflow_uid, expected_version, clean)
        if not workflow:
            raise UsersError("WORKFLOW_NOT_FOUND", "工作流不存在", 404)
        if not updated:
            raise UsersError("WORKFLOW_VERSION_CONFLICT", "工作流已在其他位置更新", 409)
        decorated = self._decorate(workflow)
        self._audit(
            "users.assets.workflow_updated",
            decorated,
            context,
            {"changedFields": sorted(clean), "version": decorated["version"]},
        )
        return {"workflow": decorated}

    def set_status(self, user_id: int, workflow_uid: str, expected_version: int, status: str, context: dict) -> dict:
        workflow, updated = self.repository.set_workflow_status(user_id, workflow_uid, expected_version, status)
        if not workflow:
            raise UsersError("WORKFLOW_NOT_FOUND", "工作流不存在", 404)
        if not updated:
            raise UsersError("WORKFLOW_VERSION_CONFLICT", "工作流已在其他位置更新", 409)
        decorated = self._decorate(workflow)
        event = "users.assets.workflow_archived" if status == "archived" else "users.assets.workflow_restored"
        self._audit(event, decorated, context, {"version": decorated["version"]})
        return {"workflow": decorated}

    def summary(self, user_id: int, limit: int = 3) -> dict:
        active_count = self.repository.count_workflows(user_id, "active")
        archived_count = self.repository.count_workflows(user_id, "archived")
        recent = self.repository.list_workflows(user_id, "active", max(1, min(limit, 5)), 0)
        return {
            "activeCount": active_count,
            "archivedCount": archived_count,
            "recent": [
                {
                    "workflowUid": item["workflowUid"],
                    "title": item["title"],
                    "availability": self._decorate(item)["availability"]["status"],
                }
                for item in recent
            ],
        }


@lru_cache(maxsize=1)
def get_assets_service() -> AssetsService:
    return AssetsService(SQLiteAssetsRepository(), get_audit_service())
