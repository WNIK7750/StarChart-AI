from pydantic import Field

from app.users.common import ResponseModel, StrictModel


class AgentModelSettingsUpdate(StrictModel):
    expectedVersion: int | None = Field(default=None, ge=1)
    providerKey: str = Field(default="custom", min_length=1, max_length=40)
    providerName: str = Field(min_length=1, max_length=60)
    baseUrl: str = Field(min_length=8, max_length=500)
    modelDisplayName: str = Field(min_length=1, max_length=200)
    modelId: str = Field(min_length=1, max_length=200)
    apiKey: str | None = Field(default=None, max_length=500)
    maxOutputTokens: int | None = Field(default=None, ge=256, le=65536)
    enabled: bool = True


class AgentModelSettingsView(ResponseModel):
    configured: bool
    providerKey: str | None = None
    providerName: str | None = None
    baseUrl: str | None = None
    modelDisplayName: str | None = None
    modelId: str | None = None
    maxOutputTokens: int | None = None
    enabled: bool = False
    hasApiKey: bool = False
    connectionStatus: str = "not_configured"
    connectionErrorCode: str | None = None
    connectionCheckedAt: str | None = None
    version: int | None = None
    allowedHosts: list[str] = Field(default_factory=list)


class AgentModelSettingsResponse(ResponseModel):
    model: AgentModelSettingsView


class AgentModelConnectionResponse(ResponseModel):
    ok: bool
    status: str
    errorCode: str | None = None
    message: str
    checkedAt: str
