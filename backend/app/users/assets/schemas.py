from typing import Literal

from pydantic import Field

from app.users.common import ResponseModel, StrictModel


class WorkflowStepInput(StrictModel):
    order: int = Field(ge=1, le=100)
    name: str = Field(min_length=1, max_length=100)
    objective: str = Field(min_length=1, max_length=500)
    toolSlug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    toolNameSnapshot: str | None = Field(default=None, max_length=100)
    toolHrefSnapshot: str | None = Field(default=None, max_length=500)


class WorkflowCreate(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=600)
    sourceType: Literal["agent", "builtin", "manual"]
    sourceRef: str | None = Field(default=None, max_length=120)
    confirmed: Literal[True]
    steps: list[WorkflowStepInput] = Field(min_length=1, max_length=30)


class WorkflowUpdate(StrictModel):
    expectedVersion: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=600)


class WorkflowStatusUpdate(StrictModel):
    expectedVersion: int = Field(ge=1)


class WorkflowTarget(ResponseModel):
    type: Literal["tool"]
    key: str
    status: Literal["available", "unavailable"]
    name: str | None
    href: str | None


class WorkflowStepResponse(ResponseModel):
    stepUid: str
    stepOrder: int
    name: str
    objective: str
    toolSlug: str | None
    toolNameSnapshot: str | None
    toolHrefSnapshot: str | None
    target: WorkflowTarget | None


class WorkflowAvailability(ResponseModel):
    status: Literal["available", "degraded"]
    unavailableTargetCount: int


class WorkflowResponseItem(ResponseModel):
    workflowUid: str
    title: str
    description: str | None
    sourceType: Literal["agent", "builtin", "manual"]
    sourceRef: str | None
    status: Literal["active", "archived"]
    version: int
    archivedAt: str | None
    createdAt: str
    updatedAt: str
    steps: list[WorkflowStepResponse]
    availability: WorkflowAvailability


class WorkflowMeta(ResponseModel):
    page: int
    pageSize: int
    totalCount: int
    hasNext: bool
    source: str
    contractVersion: int


class WorkflowListResponse(ResponseModel):
    items: list[WorkflowResponseItem]
    meta: WorkflowMeta


class WorkflowEnvelope(ResponseModel):
    workflow: WorkflowResponseItem


class WorkflowCreateMeta(ResponseModel):
    idempotencyReplayed: bool
    contractVersion: int


class WorkflowCreateResponse(WorkflowEnvelope):
    meta: WorkflowCreateMeta
