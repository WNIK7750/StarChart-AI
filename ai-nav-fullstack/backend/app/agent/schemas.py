from typing import Literal

from pydantic import BaseModel, Field

from app.users.common import StrictModel


AgentIntent = Literal["qa", "navigation", "tool_recommendation", "workflow_generation", "learning_plan"]
AgentSourceType = Literal["learning_node", "tool", "page"]


class AgentPageContext(StrictModel):
    page: str | None = None
    url: str | None = None
    nodeSlug: str | None = None
    toolCategory: str | None = None


class AgentChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    sessionId: str | None = None
    pageContext: AgentPageContext = Field(default_factory=AgentPageContext)


class AgentLinkCard(StrictModel):
    type: AgentSourceType
    sourceKey: str
    title: str
    description: str | None = None
    href: str
    reason: str | None = None
    citationIds: list[str] = Field(default_factory=list)


class AgentCitation(StrictModel):
    citationId: str
    sourceType: AgentSourceType
    sourceKey: str
    title: str
    href: str


class AgentToolCall(StrictModel):
    name: Literal["learning.search", "tools.search", "tools.workflow", "users.context"]
    status: Literal["completed", "skipped"] = "completed"
    resultCount: int = Field(default=0, ge=0)


class AgentWorkflowStep(StrictModel):
    order: int
    name: str
    objective: str
    toolSlugs: list[str] = Field(default_factory=list)
    targetHref: str | None = None
    citationIds: list[str] = Field(default_factory=list)


class AgentWorkflowDraftStep(StrictModel):
    order: int
    name: str
    objective: str
    toolSlug: str | None = None


class AgentWorkflowDraft(StrictModel):
    title: str
    description: str | None = None
    sourceType: Literal["agent"] = "agent"
    sourceRef: str | None = None
    steps: list[AgentWorkflowDraftStep] = Field(default_factory=list)


class AgentUserContextMeta(StrictModel):
    source: str
    contractVersion: int
    assets: dict = Field(default_factory=dict)
    capabilities: dict[str, bool] = Field(default_factory=dict)


class AgentResponseMeta(StrictModel):
    source: Literal["agent.deterministic"] = "agent.deterministic"
    contractVersion: int = 1
    mode: Literal["deterministic"] = "deterministic"
    readOnly: bool = True
    userContext: AgentUserContextMeta | None = None


class AgentStructuredResponse(StrictModel):
    answer: str
    intent: AgentIntent = "qa"
    cards: list[AgentLinkCard] = Field(default_factory=list)
    citations: list[AgentCitation] = Field(default_factory=list)
    toolCalls: list[AgentToolCall] = Field(default_factory=list)
    workflowSteps: list[AgentWorkflowStep] = Field(default_factory=list)
    workflowDraft: AgentWorkflowDraft | None = None
    followups: list[str] = Field(default_factory=list)
    meta: AgentResponseMeta = Field(default_factory=AgentResponseMeta)


class AgentErrorDetail(StrictModel):
    code: str
    message: str


class AgentErrorResponse(StrictModel):
    detail: AgentErrorDetail
