from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContractMeta(StrictModel):
    contractVersion: int = 1


class KnowledgeDomain(StrictModel):
    code: str
    name: str
    color: str
    glowColor: str
    description: str | None = None


class DifficultyLevel(StrictModel):
    code: str
    name: str
    color: str


class RoadmapNode(StrictModel):
    slug: str
    title: str
    subtitle: str
    difficultyCode: str
    color: str
    x: int
    y: int
    width: int
    height: int
    isCurrent: bool


class RoadmapEdge(StrictModel):
    fromSlug: str
    toSlug: str
    pathD: str
    lineType: str
    relationType: str


class RoadmapResponse(StrictModel):
    domains: list[KnowledgeDomain]
    difficultyLevels: list[DifficultyLevel]
    nodes: list[RoadmapNode]
    edges: list[RoadmapEdge]
    domainNodes: dict[str, list[str]]
    viewBox: str
    meta: ContractMeta


class LearningResource(StrictModel):
    slug: str
    title: str
    description: str
    coverLabel: str
    coverText: str
    coverTheme: str
    href: str
    nodeSlug: str | None = None


class LearningResourcesResponse(StrictModel):
    items: list[LearningResource]
    meta: ContractMeta


class NodeSummary(StrictModel):
    slug: str
    title: str


class LearningNode(StrictModel):
    slug: str
    title: str
    subtitle: str
    difficultyCode: str
    difficultyName: str
    color: str


class MainMaterial(StrictModel):
    title: str
    provider: str
    materialType: str
    url: str
    startUrl: str
    language: str
    accessType: str
    coverLabel: str
    coverText: str
    coverTheme: str
    description: str
    overview: str
    materialId: int
    materialUid: str
    publicationStatus: str
    contentVersion: int = Field(ge=1)
    qualityStatus: str
    sourceTrust: str
    lastVerifiedAt: str | None = None
    linkStatus: str

    @field_validator("url", "startUrl")
    @classmethod
    def validate_external_url(cls, value: str) -> str:
        if urlsplit(value).scheme not in {"http", "https"}:
            raise ValueError("Material URL must use http or https")
        return value


class NodeOverview(StrictModel):
    title: str
    body: str


class MaterialSection(StrictModel):
    sectionId: int
    sectionUid: str
    chapterNo: int
    sectionNo: int
    title: str
    description: str
    durationMinutes: int = Field(ge=0)
    sourceUrl: str | None = None

    @field_validator("sourceUrl")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value and urlsplit(value).scheme not in {"http", "https"}:
            raise ValueError("Section URL must use http or https")
        return value


class NodeResource(StrictModel):
    linkId: int
    linkUid: str
    title: str
    description: str
    url: str
    linkType: str
    accessType: str
    accentColor: str
    publicationStatus: str
    qualityStatus: str
    lastCheckedAt: str | None = None
    linkStatus: str

    @field_validator("url")
    @classmethod
    def validate_resource_url(cls, value: str) -> str:
        if urlsplit(value).scheme not in {"http", "https"}:
            raise ValueError("Resource URL must use http or https")
        return value


class NodeStats(StrictModel):
    chapterCount: int = Field(ge=0)
    sectionCount: int = Field(ge=0)
    suggestedMinutes: int = Field(ge=0)
    suggestedDuration: str


class NodeNavigation(StrictModel):
    previous: NodeSummary | None = None
    next: NodeSummary | None = None


class NodeRelationItem(StrictModel):
    slug: str
    title: str
    subtitle: str
    difficultyCode: str
    relationType: str
    href: str


class NodeRelations(StrictModel):
    prerequisites: list[NodeRelationItem]
    recommendedNext: list[NodeRelationItem]
    related: list[NodeRelationItem]


class NodeRelationsResponse(StrictModel):
    nodeSlug: str
    relations: NodeRelations
    meta: ContractMeta


class NodeMeta(ContractMeta):
    sourceMaterialId: int
    durationRule: str


class LearningNodeResponse(StrictModel):
    node: LearningNode
    mainMaterial: MainMaterial
    overview: NodeOverview
    outline: list[MaterialSection]
    resources: list[NodeResource]
    tags: list[str]
    stats: NodeStats
    navigation: NodeNavigation
    relations: NodeRelations
    meta: NodeMeta


class LearningSearchItem(StrictModel):
    slug: str
    title: str
    subtitle: str
    difficultyCode: str
    difficultyName: str
    summary: str
    href: str


class LearningSearchResponse(StrictModel):
    query: str
    items: list[LearningSearchItem]
    meta: ContractMeta


class LearningEvidence(StrictModel):
    sourceType: str
    sourceKey: str


class AgentLearningNode(StrictModel):
    slug: str
    title: str
    summary: str
    difficultyCode: str
    href: str
    prerequisiteSlugs: list[str]
    recommendedNextSlugs: list[str]
    evidence: LearningEvidence


class AgentLearningContextResponse(StrictModel):
    query: str
    nodes: list[AgentLearningNode]
    meta: ContractMeta


class NextLearningNode(StrictModel):
    slug: str
    title: str
    subtitle: str
    difficultyCode: str
    href: str


class NextLearningNodeResponse(StrictModel):
    item: NextLearningNode | None = None
    meta: ContractMeta
