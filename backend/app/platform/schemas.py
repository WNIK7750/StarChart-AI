from pydantic import BaseModel, ConfigDict


class StrictResponseModel(BaseModel):
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
