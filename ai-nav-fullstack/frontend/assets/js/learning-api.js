import { apiDelete, apiGet, apiPost, apiPut } from "./api.js";

export const getLearningRoadmap = () => apiGet("/learning/roadmap");
export const listLearningResources = (domain = "") => apiGet("/learning/resources", { domain });
export const getLearningNode = (slug) => apiGet(`/learning/nodes/${encodeURIComponent(slug)}`);

export const getLearningDashboard = () => apiGet("/users/me/learning/dashboard");
export const listLearningProgress = () => apiGet("/users/me/learning/progress");
export const getLearningNodeState = (slug) => apiGet(`/users/me/learning/nodes/${encodeURIComponent(slug)}`);
export const updateLearningProgress = (slug, payload) => apiPut(`/users/me/learning/progress/${encodeURIComponent(slug)}`, payload);
export const updateLearningSection = (slug, sectionUid, payload) => apiPut(
  `/users/me/learning/nodes/${encodeURIComponent(slug)}/sections/${encodeURIComponent(sectionUid)}`,
  payload,
);
export const recordLearningActivity = (payload, idempotencyKey) => apiPost(
  "/users/me/learning/activity",
  payload,
  { headers: { "Idempotency-Key": idempotencyKey } },
);
export const importAnonymousLearning = (payload) => apiPost("/users/me/learning/import", payload);
export const listRecentLearning = (params = {}) => apiGet("/users/me/learning/recent", params);

export const listLearningFavorites = (params = {}) => apiGet("/users/me/favorites", params);
export const addLearningFavorite = (targetType, targetKey) => apiPost("/users/me/favorites", { targetType, targetKey });
export const removeLearningFavorite = (favoriteUid) => apiDelete(`/users/me/favorites/${encodeURIComponent(favoriteUid)}`);
