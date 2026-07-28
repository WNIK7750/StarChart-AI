from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field, field_validator, model_validator

from app.users.common import ResponseModel, StrictModel


AgentIntent = Literal["qa", "navigation", "tool_recommendation", "workflow_generation", "learning_plan"]
AgentSourceType = Literal["learning_node", "tool", "page"]
AgentHistoryRole = Literal["user", "assistant"]


class AgentPageContext(StrictModel):
    page: str | None = Field(default=None, max_length=64)
    url: str | None = Field(default=None, max_length=512)
    nodeSlug: str | None = Field(default=None, max_length=100)
    toolCategory: str | None = Field(default=None, max_length=100)

    @field_validator("url")
    @classmethod
    def validate_relative_url(cls, value: str | None) -> str | None:
        if not value:
            return value
        if value != value.strip() or any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("url must be a relative same-origin path")

        candidate = value
        for _ in range(len(value) + 1):
            decoded = unquote(candidate)
            if decoded == candidate:
                break
            candidate = decoded

        parsed = urlsplit(candidate)
        path_segments = parsed.path.split("/")
        if (
            any(ord(character) < 32 or ord(character) == 127 for character in candidate)
            or parsed.scheme
            or parsed.netloc
            or candidate.startswith("//")
            or "\\" in candidate
            or ".." in path_segments
        ):
            raise ValueError("url must be a relative same-origin path")
        return value


class AgentChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    sessionId: str | None = Field(default=None, max_length=128)
    pageContext: AgentPageContext = Field(default_factory=AgentPageContext)


class AgentHistoryMessage(StrictModel):
    role: AgentHistoryRole
    content: str = Field(min_length=1, max_length=6000)


class AgentGuestChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AgentHistoryMessage] = Field(default_factory=list, max_length=12)
    pageContext: AgentPageContext = Field(default_factory=AgentPageContext)

    @model_validator(mode="after")
    def validate_history_budget(self):
        if sum(len(message.content) for message in self.history) > 12000:
            raise ValueError("history must contain at most 12000 characters")
        return self


class AgentCapabilities(StrictModel):
    stream: bool
    sessions: bool = False
    transportVersion: int = 1


class AgentRuntimeProvider(StrictModel):
    mode: Literal[
        "deterministic",
        "fake",
        "configured_off",
        "live",
        "invalid",
    ]
    model: str | None
    live: bool
    configurationValid: bool
    upgradeModel: str | None
    upgradeRatio: float = Field(ge=0, le=1)


class AgentRuntimeFeatures(StrictModel):
    stream: bool
    sessions: bool
    responseReplay: bool
    observability: bool
    openAICompatibleIncremental: bool


class AgentRuntimeSafety(StrictModel):
    automaticRequestRetry: Literal[False] = False
    providerConsentRequired: Literal[True] = True
    upgradeRoutingEnabled: Literal[False] = False
    singleWorkerEnforced: Literal[True] = True


class AgentRuntimeTopology(StrictModel):
    declaredWorkers: int = Field(ge=1)
    stateBackend: Literal["process_local"]


class AgentRuntimeMeta(StrictModel):
    source: Literal["agent.runtime"] = "agent.runtime"
    containsSecrets: Literal[False] = False
    containsProviderEndpoint: Literal[False] = False


class AgentRuntimeProfile(StrictModel):
    contractVersion: Literal[1] = 1
    provider: AgentRuntimeProvider
    features: AgentRuntimeFeatures
    safety: AgentRuntimeSafety
    topology: AgentRuntimeTopology
    meta: AgentRuntimeMeta = Field(default_factory=AgentRuntimeMeta)


class AgentSessionCreate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class AgentSessionSummary(StrictModel):
    sessionId: str
    title: str
    messageCount: int = Field(ge=0)
    pinned: bool = False
    pinnedAt: str | None = None
    expiresAt: str
    createdAt: str
    updatedAt: str


class AgentSessionMessage(StrictModel):
    messageId: str
    role: Literal["user", "assistant"]
    content: str
    createdAt: str


class AgentSessionPageMeta(StrictModel):
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    totalCount: int = Field(ge=0)
    hasNext: bool
    contractVersion: Literal[1] = 1


class AgentSessionCreateResponse(StrictModel):
    session: AgentSessionSummary


class AgentSessionUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    pinned: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.title is None and self.pinned is None:
            raise ValueError("at least one session field must be provided")
        return self


class AgentSessionUpdateResponse(StrictModel):
    session: AgentSessionSummary


class AgentSessionListResponse(StrictModel):
    items: list[AgentSessionSummary]
    meta: AgentSessionPageMeta


class AgentSessionDetailResponse(StrictModel):
    session: AgentSessionSummary
    messages: list[AgentSessionMessage]
    meta: AgentSessionPageMeta


class AgentLongConversationSummary(StrictModel):
    conversationId: str
    title: str
    messageCount: int = Field(ge=0)
    pinned: bool = False
    pinnedAt: str | None = None
    createdAt: str
    updatedAt: str


class AgentSessionUpgradeResponse(StrictModel):
    conversation: AgentLongConversationSummary


class AgentLongConversationUpdateResponse(StrictModel):
    conversation: AgentLongConversationSummary


class AgentLongConversationListResponse(StrictModel):
    items: list[AgentLongConversationSummary]
    meta: AgentSessionPageMeta


class AgentLongConversationDetailResponse(StrictModel):
    conversation: AgentLongConversationSummary
    messages: list[AgentSessionMessage]
    meta: AgentSessionPageMeta


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
    name: Literal[
        "learning.search",
        "tools.search",
        "tools.workflow",
        "users.context",
        "navigation.read",
    ]
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


class AgentUserContextRecentAsset(StrictModel):
    workflowUid: str
    title: str
    availability: Literal["available", "degraded"]


class AgentUserContextAssets(StrictModel):
    activeCount: int = 0
    archivedCount: int = 0
    recent: list[AgentUserContextRecentAsset] = Field(default_factory=list)


class AgentUserContextCapabilities(StrictModel):
    agentChat: bool = False
    saveWorkflow: bool = False


class AgentUserContextMeta(StrictModel):
    source: str
    contractVersion: int
    assets: AgentUserContextAssets
    capabilities: AgentUserContextCapabilities


class AgentResponseMeta(StrictModel):
    source: Literal["agent.deterministic", "agent.provider"] = "agent.deterministic"
    contractVersion: int = 1
    mode: Literal["deterministic", "provider"] = "deterministic"
    readOnly: bool = True
    userContext: AgentUserContextMeta | None = None
    provider: str | None = None
    model: str | None = None
    promptVersion: str | None = None
    fallbackReason: Literal[
        "not_configured",
        "cancelled",
        "timeout",
        "authentication",
        "rate_limited",
        "capacity_limited",
        "budget_exceeded",
        "consent_required",
        "unavailable",
        "invalid_output",
        "insufficient_evidence",
        "sensitive_input",
    ] | None = None
    attempts: int = Field(default=0, ge=0, le=2)


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


class AgentStreamEvent(StrictModel):
    event: Literal[
        "response.started",
        "response.answer.delta",
        "response.completed",
    ]
    sequence: int = Field(ge=0)
    requestId: str = Field(min_length=1, max_length=128)
    delta: str | None = Field(default=None, min_length=1, max_length=1000)
    response: AgentStructuredResponse | None = None

    @model_validator(mode="after")
    def validate_event_payload(self):
        if self.event == "response.answer.delta":
            if self.delta is None or self.response is not None:
                raise ValueError("answer delta events require only delta")
        elif self.event == "response.completed":
            if self.response is None or self.delta is not None:
                raise ValueError("completed events require only response")
        elif self.delta is not None or self.response is not None:
            raise ValueError("started events cannot contain payload")
        return self


class AgentErrorDetail(StrictModel):
    code: str
    message: str


class AgentErrorResponse(StrictModel):
    detail: AgentErrorDetail


class AgentMetricOutcome(ResponseModel):
    outcome: str
    fallbackReason: str
    count: int


class AgentMetricModel(ResponseModel):
    provider: str
    model: str
    count: int


class AgentMetricRecent(ResponseModel):
    requestCount: int
    providerSuccessCount: int
    fallbackCount: int
    inputTokens: int
    outputTokens: int
    costCny: float
    latencyP50Ms: float
    latencyP95Ms: float


class AgentMetricCounters(ResponseModel):
    outcomes: list[AgentMetricOutcome]
    models: list[AgentMetricModel]
    replayHits: int
    requestIdConflicts: int


class AgentMetricAlert(ResponseModel):
    code: str
    count: int | None = None
    value: float | None = None
    threshold: float


class AgentMetricMeta(ResponseModel):
    source: str
    containsPii: bool
    containsContent: bool
    processLocal: bool


class AgentMetricsResponse(ResponseModel):
    windowSeconds: int
    recent: AgentMetricRecent
    counters: AgentMetricCounters
    alerts: list[AgentMetricAlert]
    meta: AgentMetricMeta
