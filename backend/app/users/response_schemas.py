from typing import Literal

from app.users.common import ResponseModel as StrictModel


class AccountItem(StrictModel):
    userUid: str
    username: str
    email: str | None
    phone: str | None
    emailVerified: bool
    phoneVerified: bool
    accountStatus: str
    updatedAt: str


class AccountResponse(StrictModel):
    account: AccountItem


class AccountUpdateMeta(StrictModel):
    changedFields: list[str]


class AccountUpdateResponse(AccountResponse):
    meta: AccountUpdateMeta


class ProfileItem(StrictModel):
    displayName: str
    avatarUrl: str | None
    bio: str | None
    roleTitle: str | None
    learningLevel: str
    targetDirection: str | None
    version: int
    updatedAt: str


class ProfileResponse(StrictModel):
    profile: ProfileItem


class AvatarMeta(StrictModel):
    originalBytes: int
    storedBytes: int
    originalWidth: int
    originalHeight: int
    width: int
    height: int
    format: Literal["webp"]
    oldAvatarRemoved: bool


class AvatarUploadResponse(ProfileResponse):
    avatarUrl: str
    meta: AvatarMeta


class PreferencesItem(StrictModel):
    theme: str
    language: str
    cnFirst: bool
    freeFirst: bool
    showExternalResources: bool
    agentMemoryEnabled: bool
    preferenceJson: str | None
    version: int
    updatedAt: str


class PreferencesResponse(StrictModel):
    preferences: PreferencesItem


class PreferenceContextItem(StrictModel):
    language: str
    cnFirst: bool
    freeFirst: bool
    showExternalResources: bool
    agentMemoryEnabled: bool | None = None


class PreferenceContextMeta(StrictModel):
    source: str
    contractVersion: int
    consumer: Literal["learning", "tools", "agent"]
    version: int


class PreferenceContextResponse(StrictModel):
    preferences: PreferenceContextItem
    meta: PreferenceContextMeta


class SecurityQuestionResponseItem(StrictModel):
    questionOrder: int
    question: str
    updatedAt: str


class SecurityQuestionsResponse(StrictModel):
    configured: bool
    items: list[SecurityQuestionResponseItem]


class SessionItem(StrictModel):
    sessionUid: str
    deviceName: str | None
    userAgent: str | None
    ipAddress: str | None
    isRevoked: bool
    expiresAt: str
    lastSeenAt: str | None
    createdAt: str
    revokedReason: str | None
    isCurrent: bool
    riskLevel: str


class SessionListMeta(StrictModel):
    page: int
    pageSize: int
    totalCount: int
    hasNext: bool
    source: str
    contractVersion: int


class SessionListResponse(StrictModel):
    items: list[SessionItem]
    meta: SessionListMeta


class StatusResponse(StrictModel):
    status: str


class StatusMessageResponse(StatusResponse):
    message: str


class RevokeOtherSessionsResponse(StatusResponse):
    revokedCount: int


class ConsentItem(StrictModel):
    consentType: str
    policyVersion: str
    status: Literal["granted", "revoked"]
    recordedPolicyVersion: str | None = None
    recordedAt: str | None
    source: str | None


class ConsentResponse(StrictModel):
    consent: ConsentItem


class PrivacyMeta(StrictModel):
    source: str
    contractVersion: int


class ConsentStatusResponse(StrictModel):
    items: list[ConsentItem]
    meta: PrivacyMeta


class DataRequestItem(StrictModel):
    requestUid: str
    requestType: str | None = None
    status: str | None = None
    reasonCode: str | None = None
    scheduledFor: str | None = None
    retentionUntil: str | None = None
    completedAt: str | None = None
    cancelledAt: str | None = None
    createdAt: str | None = None
    updatedAt: str | None = None


class DataRequestResponse(StrictModel):
    request: DataRequestItem | None


class ExportAccount(StrictModel):
    userUid: str
    username: str
    email: str | None
    phone: str | None
    accountStatus: str
    emailVerified: bool
    phoneVerified: bool
    lastLoginAt: str | None
    createdAt: str
    updatedAt: str


class ExportProfile(StrictModel):
    displayName: str
    avatarUrl: str | None
    bio: str | None
    roleTitle: str | None
    learningLevel: str
    targetDirection: str | None
    createdAt: str
    updatedAt: str


class ExportPreferences(StrictModel):
    theme: str
    language: str
    cnFirst: bool
    freeFirst: bool
    showExternalResources: bool
    createdAt: str
    updatedAt: str


class ExportSecurityQuestion(StrictModel):
    questionOrder: int
    question: str
    createdAt: str


class ExportSession(StrictModel):
    sessionUid: str
    deviceName: str | None
    countryRegion: str | None
    isRevoked: bool
    revokedAt: str | None
    expiresAt: str
    lastSeenAt: str | None
    createdAt: str


class ExportLearningProgress(StrictModel):
    nodeSlug: str
    status: str
    progressPercent: int
    startedAt: str | None
    completedAt: str | None
    lastStudiedAt: str | None
    createdAt: str
    updatedAt: str


class ExportLearningActivity(StrictModel):
    activityUid: str
    nodeSlug: str | None
    targetType: str
    targetKey: str
    activityType: str
    createdAt: str


class ExportFavorite(StrictModel):
    favoriteUid: str
    targetType: str
    targetKey: str
    title: str
    description: str | None
    createdAt: str


class ExportWorkflow(StrictModel):
    workflowUid: str
    title: str
    description: str | None
    sourceType: str
    sourceRef: str | None
    status: str
    version: int
    archivedAt: str | None
    createdAt: str
    updatedAt: str


class ExportAgentMessage(StrictModel):
    messageUid: str
    role: str
    content: str
    createdAt: str


class ExportAgentShortConversation(StrictModel):
    sessionUid: str
    title: str
    titleCustomized: bool
    pinnedAt: str | None
    expiresAt: str
    createdAt: str
    updatedAt: str
    messages: list[ExportAgentMessage]


class ExportAgentLongConversation(StrictModel):
    conversationUid: str
    title: str
    pinnedAt: str | None
    createdAt: str
    updatedAt: str
    messages: list[ExportAgentMessage]


class ExportConsentEvent(StrictModel):
    eventUid: str
    consentType: str
    policyVersion: str
    action: str
    source: str
    createdAt: str


class ExportAuditEvent(StrictModel):
    action: str
    resourceType: str
    resourceId: str | None
    createdAt: str


class ExportData(StrictModel):
    account: ExportAccount
    profile: ExportProfile
    preferences: ExportPreferences
    securityQuestions: list[ExportSecurityQuestion]
    sessions: list[ExportSession]
    learningProgress: list[ExportLearningProgress]
    learningActivity: list[ExportLearningActivity]
    favorites: list[ExportFavorite]
    savedWorkflows: list[ExportWorkflow]
    agentShortConversations: list[ExportAgentShortConversation]
    agentLongConversations: list[ExportAgentLongConversation]
    consentEvents: list[ExportConsentEvent]
    dataRequests: list[DataRequestItem]
    auditEvents: list[ExportAuditEvent]


class ExportPayload(StrictModel):
    format: Literal["application/json"]
    formatVersion: int
    generatedAt: str
    data: ExportData


class DataExportResponse(StrictModel):
    request: DataRequestItem
    export: ExportPayload


class DeletionAdminResponse(StrictModel):
    userId: int
    userUid: str
    request: DataRequestItem


class DeletionAnonymizeResponse(DeletionAdminResponse):
    avatarUrl: str | None


class UsersMetricCounter(StrictModel):
    operation: str
    outcome: str
    errorCode: str
    count: int


class UsersMetricAlert(StrictModel):
    code: str
    operation: str
    count: int
    threshold: int


class UsersMetricsMeta(StrictModel):
    source: str
    containsPii: bool


class UsersMetricsResponse(StrictModel):
    windowSeconds: int
    counters: list[UsersMetricCounter]
    alerts: list[UsersMetricAlert]
    meta: UsersMetricsMeta
