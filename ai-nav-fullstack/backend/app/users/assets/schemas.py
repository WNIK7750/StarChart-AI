from typing import Literal

from pydantic import Field

from app.users.common import StrictModel


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
