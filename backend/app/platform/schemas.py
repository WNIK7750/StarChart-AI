from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StrictResponseModel(StrictModel):
    model_config = ConfigDict(extra="ignore")


class NavigationItem(StrictResponseModel):
    code: str
    label: str
    href: str


class NavigationResponse(StrictResponseModel):
    items: list[NavigationItem]


class HealthResponse(StrictResponseModel):
    status: str


class ReadinessResponse(StrictResponseModel):
    status: str
    migrationCount: int


class PublicAuthCapabilities(StrictModel):
    registration: bool
    recovery: bool
    identityChanges: bool
    privacyWrites: bool


class PublicAgentCapabilities(StrictModel):
    guestChat: bool
    authenticatedSessions: bool


class PublicRuntimeCapabilities(StrictModel):
    deploymentProfile: str
    publicBasePath: str
    auth: PublicAuthCapabilities
    agent: PublicAgentCapabilities
