import { clearAuthTokens, getAccessToken, restoreAuthSession } from "./api.js";
import { getCurrentUser, getUserProfile } from "./users-api.js";
import { createAuthSessionStore } from "./auth-session-store-core.js";

async function resolveBrowserSession() {
  if (!getAccessToken()) await restoreAuthSession();
  const [{ user }, profileResult] = await Promise.all([
    getCurrentUser(),
    getUserProfile().catch(() => ({ profile: {} })),
  ]);
  return { user, profile: profileResult.profile || {} };
}

const store = createAuthSessionStore(resolveBrowserSession);

export function getAuthSessionSnapshot() {
  return store.getSnapshot();
}

export function subscribeAuthSession(listener) {
  return store.subscribe(listener);
}

export function initializeAuthSession() {
  return store.initialize();
}

export function refreshAuthSession() {
  return store.initialize({ force: true });
}

export function clearAuthSession(error = null) {
  clearAuthTokens();
  return store.setUnauthenticated(error);
}

if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
  window.addEventListener("ai-nav-auth-changed", () => {
    if (getAccessToken()) void initializeAuthSession();
    else store.setUnauthenticated();
  });
}
