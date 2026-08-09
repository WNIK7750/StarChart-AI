from pydantic import BaseModel, ConfigDict, Field


class StrictResponseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ToolCategory(StrictResponseModel):
    id: str
    name: str
    icon: str
    logoClass: str
    description: str
    subcategories: list[str]


class ToolPlacement(StrictResponseModel):
    toolId: str
    categoryId: str
    subcategory: str
    heat: int
    tag: str | None


class ToolItem(StrictResponseModel):
    id: str
    name: str
    aliases: list[str]
    description: str
    mark: str
    url: str
    icon: str
    iconFallbacks: list[str]
    isFree: bool
    publicationStatus: str
    linkStatus: str
    lastCheckedAt: str | None
    categories: list[str]
    subcategories: list[str]
    tags: list[str]
    heat: int
    href: str


class ToolCatalogMeta(StrictResponseModel):
    source: str
    contractVersion: int
    catalogVersion: int
    catalogFingerprint: str
    publishedToolCount: int
    placementCount: int
    readiness: str


class ToolCatalogResponse(StrictResponseModel):
    version: int
    categories: list[ToolCategory]
    tools: list[ToolItem]
    placements: list[ToolPlacement]
    latestTools: list["LatestToolSlot"]
    meta: ToolCatalogMeta


class ToolCategoriesResponse(StrictResponseModel):
    items: list[ToolCategory]


class ToolSearchItem(StrictResponseModel):
    type: str
    title: str
    description: str
    href: str
    iconUrl: str | None
    iconFallbacks: list[str]
    mark: str | None
    score: float
    reason: str
    matchedCapabilities: list[str] = Field(default_factory=list)
    reasonCodes: list[str] = Field(default_factory=list)
    tool: ToolItem


class ToolSearchResponse(StrictResponseModel):
    items: list[ToolSearchItem]
    query: str


class AgentToolItem(StrictResponseModel):
    id: str
    name: str
    description: str
    categories: list[str]
    tags: list[str]
    url: str
    href: str
    reason: str
    matchedCapabilities: list[str] = Field(default_factory=list)
    reasonCodes: list[str] = Field(default_factory=list)


class WorkflowSuggestion(StrictResponseModel):
    code: str
    title: str
    description: str
    toolNames: list[str]
    tools: list[ToolItem]


class AgentToolContextResponse(StrictResponseModel):
    query: str
    tools: list[AgentToolItem]
    workflows: list[WorkflowSuggestion]


class ToolListResponse(StrictResponseModel):
    items: list[ToolItem]
    page: int
    pageSize: int
    total: int


class LatestToolSlot(StrictResponseModel):
    displayName: str
    toolName: str
    provider: str
    label: str
    mark: str
    logoClass: str


class LatestToolItem(LatestToolSlot):
    tool: ToolItem


class LatestToolsResponse(StrictResponseModel):
    items: list[LatestToolItem]


class WorkflowSuggestionsResponse(StrictResponseModel):
    items: list[WorkflowSuggestion]
