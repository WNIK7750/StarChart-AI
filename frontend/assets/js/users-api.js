import { apiDelete, apiGet, apiPatch, apiPost, apiPut, apiUpload } from "./api.js";

export const getCurrentUser = () => apiGet("/auth/me");
export const loginUser = (payload) => apiPost("/auth/login", payload);
export const registerUser = (payload) => apiPost("/auth/register", payload);
export const logoutUser = () => apiPost("/auth/logout", {});
export const startPasswordReset = (payload) => apiPost("/auth/password-reset/start", payload);
export const confirmPasswordReset = (payload) => apiPost("/auth/password-reset/confirm", payload);

export const getUserAccount = () => apiGet("/users/me/account");
export const updateUserAccount = (payload) => apiPatch("/users/me/account", payload);
export const updateUserPassword = (payload) => apiPatch("/users/me/password", payload);
export const getUserProfile = () => apiGet("/users/me/profile");
export const updateUserProfile = (payload) => apiPatch("/users/me/profile", payload);
export const uploadUserAvatar = (formData) => apiUpload("/users/me/avatar", formData);
export const getUserPreferences = () => apiGet("/users/me/preferences");
export const getUserPreferenceContext = (consumer) => apiGet("/users/me/preferences/context", { consumer });
export const updateUserPreferences = (payload) => apiPatch("/users/me/preferences", payload);
export const getUserPrivacyConsents = () => apiGet("/users/me/privacy/consents");
export const updateUserPrivacyConsent = (consentType, payload) => apiPut(
  `/users/me/privacy/consents/${encodeURIComponent(consentType)}`,
  payload,
);
export const exportUserData = (currentPassword) => apiPost("/users/me/privacy/export", { currentPassword });
export const getCurrentDeletionRequest = () => apiGet("/users/me/privacy/deletion-requests/current");
export const requestUserDeletion = (payload) => apiPost("/users/me/privacy/deletion-requests", payload);
export const cancelUserDeletion = (requestUid) => apiDelete(
  `/users/me/privacy/deletion-requests/${encodeURIComponent(requestUid)}`,
);
export const getUserSecurityQuestions = () => apiGet("/users/me/security-questions");
export const updateUserSecurityQuestions = (payload) => apiPut("/users/me/security-questions", payload);
export const listUserSessions = (params = {}) => apiGet("/users/me/sessions", params);
export const revokeUserSession = (sessionUid) => apiDelete(`/users/me/sessions/${encodeURIComponent(sessionUid)}`);
export const revokeOtherUserSessions = () => apiPost("/users/me/sessions/revoke-others", {});
export const listUserWorkflows = (params = {}) => apiGet("/users/me/assets/workflows", params);
export const archiveUserWorkflow = (workflowUid, expectedVersion) => apiPost(
  `/users/me/assets/workflows/${encodeURIComponent(workflowUid)}/archive`,
  { expectedVersion },
);
export const restoreUserWorkflow = (workflowUid, expectedVersion) => apiPost(
  `/users/me/assets/workflows/${encodeURIComponent(workflowUid)}/restore`,
  { expectedVersion },
);
export const saveAgentWorkflow = (payload, idempotencyKey) => apiPost(
  "/agent/workflows/save",
  payload,
  { headers: { "Idempotency-Key": idempotencyKey } },
);
