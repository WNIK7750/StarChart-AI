from pydantic import BaseModel, Field


class AgentPageContext(BaseModel):
    page: str | None = None
    url: str | None = None
    nodeSlug: str | None = None
    toolCategory: str | None = None


class AgentPreferences(BaseModel):
    cnFirst: bool = True
    freeFirst: bool = False
    experienceLevel: str = "beginner"


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    sessionId: str | None = None
    pageContext: AgentPageContext = Field(default_factory=AgentPageContext)
    preferences: AgentPreferences = Field(default_factory=AgentPreferences)


class AgentLinkCard(BaseModel):
    type: str
    title: str
    description: str | None = None
    href: str


class AgentWorkflowStep(BaseModel):
    order: int
    name: str
    objective: str
    toolSlugs: list[str] = Field(default_factory=list)


class AgentStructuredResponse(BaseModel):
    answer: str
    intent: str = "qa"
    cards: list[AgentLinkCard] = Field(default_factory=list)
    workflowSteps: list[AgentWorkflowStep] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)
