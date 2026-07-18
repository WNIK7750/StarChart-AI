import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserStateMeta(StrictModel):
    source: str = "users.learning_state"
    contractVersion: int = 1


class PageMeta(UserStateMeta):
    page: int = Field(ge=1)
    pageSize: int = Field(ge=1)
    totalCount: int = Field(ge=0)
    hasNext: bool


class ProgressItem(StrictModel):
    nodeSlug: str
    status: str
    progressPercent: int = Field(ge=0, le=100)
    startedAt: str | None = None
    completedAt: str | None = None
    lastStudiedAt: str | None = None
    version: int = Field(ge=1)
    updatedAt: str
    title: str
    description: str | None = None
    href: str


class ProgressListResponse(StrictModel):
    items: list[ProgressItem]
    meta: UserStateMeta


class ProgressResponse(StrictModel):
    progress: ProgressItem


class SectionProgressItem(StrictModel):
    sectionUid: str
    nodeSlug: str
    isCompleted: bool
    completedAt: str | None = None
    version: int = Field(ge=0)
    updatedAt: str | None = None
    chapterNo: int = Field(ge=1)
    sectionNo: int = Field(ge=1)
    title: str


class SectionProgressSummary(StrictModel):
    completedCount: int = Field(ge=0)
    totalCount: int = Field(ge=0)
    progressPercent: int = Field(ge=0, le=100)


class NodeLearningStateResponse(StrictModel):
    nodeSlug: str
    progress: ProgressItem | None = None
    sections: list[SectionProgressItem]
    summary: SectionProgressSummary
    meta: UserStateMeta


class SectionProgressResponse(StrictModel):
    section: SectionProgressItem
    progress: ProgressItem
    summary: SectionProgressSummary


class SectionProgressUpdate(StrictModel):
    isCompleted: bool
    expectedVersion: int | None = Field(default=None, ge=0)


class ActivityItem(StrictModel):
    activityUid: str
    nodeSlug: str | None = None
    targetType: str
    targetKey: str
    activityType: str
    createdAt: str
    title: str
    description: str | None = None
    href: str | None = None
    isAvailable: bool
    idempotencyReplayed: bool = False


class ActivityResponse(StrictModel):
    activity: ActivityItem


class RecentItem(StrictModel):
    activityUid: str
    nodeSlug: str | None = None
    targetType: str
    targetKey: str
    activityType: str
    lastReadAt: str
    title: str
    description: str | None = None
    href: str | None = None
    isAvailable: bool


class RecentResponse(StrictModel):
    items: list[RecentItem]
    meta: PageMeta


class FavoriteItem(StrictModel):
    favoriteUid: str
    targetType: str
    targetKey: str
    titleSnapshot: str
    descriptionSnapshot: str | None = None
    createdAt: str
    title: str
    description: str | None = None
    href: str | None = None
    isAvailable: bool


class FavoriteResponse(StrictModel):
    favorite: FavoriteItem


class FavoritesResponse(StrictModel):
    items: list[FavoriteItem]
    meta: PageMeta


class ResumeItem(StrictModel):
    title: str
    href: str
    reasonCode: str
    description: str | None = None
    nodeSlug: str | None = None
    slug: str | None = None
    status: str | None = None
    progressPercent: int | None = Field(default=None, ge=0, le=100)
    startedAt: str | None = None
    completedAt: str | None = None
    lastStudiedAt: str | None = None
    version: int | None = None
    updatedAt: str | None = None
    activityUid: str | None = None
    targetType: str | None = None
    targetKey: str | None = None
    activityType: str | None = None
    lastReadAt: str | None = None
    isAvailable: bool | None = None
    subtitle: str | None = None
    difficultyCode: str | None = None
    difficultyName: str | None = None
    summary: str | None = None


class ResumeResponse(StrictModel):
    item: ResumeItem | None = None


class LearningSummary(StrictModel):
    startedCount: int = Field(ge=0)
    completedCount: int = Field(ge=0)
    overallPercent: int = Field(ge=0, le=100)


class DashboardResponse(StrictModel):
    resume: ResumeItem | None = None
    recent: list[RecentItem]
    favorites: list[FavoriteItem]
    summary: LearningSummary
    meta: UserStateMeta


class ProgressUpdate(StrictModel):
    progressPercent: int = Field(ge=0, le=100)
    status: str | None = Field(default=None, pattern="^(not_started|in_progress|completed|skipped)$")
    expectedVersion: int | None = Field(default=None, ge=1)


class ActivityCreate(StrictModel):
    nodeSlug: str | None = Field(default=None, max_length=100)
    targetType: str = Field(pattern="^(learning_node|learning_material|learning_link)$")
    targetKey: str = Field(min_length=1, max_length=100)
    activityType: str = Field(pattern="^(view_node|start_material|open_resource|complete_section)$")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20 or len(json.dumps(value, ensure_ascii=False)) > 4096:
            raise ValueError("metadata exceeds the allowed size")
        return value


class FavoriteCreate(StrictModel):
    targetType: str = Field(pattern="^(learning_node|learning_material|learning_link)$")
    targetKey: str = Field(min_length=1, max_length=100)


class AnonymousNodeView(StrictModel):
    nodeSlug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    viewedAt: datetime


class AnonymousLearningImport(StrictModel):
    snapshotId: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    nodeViews: list[AnonymousNodeView] = Field(max_length=30)


class AnonymousLearningImportResult(StrictModel):
    importedActivityCount: int = Field(ge=0)
    replayedActivityCount: int = Field(ge=0)
    meta: UserStateMeta
