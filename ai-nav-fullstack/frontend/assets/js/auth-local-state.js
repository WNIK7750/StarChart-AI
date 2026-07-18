const PRIVACY_CONSENT_KEY = "ai_nav_privacy_consent_2026-07-01";
const RECENT_AVATAR_KEY = "ai_nav_recent_avatar_v1";

function read(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    if (value) window.localStorage.setItem(key, value);
    else window.localStorage.removeItem(key);
  } catch {
    // Authentication must remain usable when storage is unavailable.
  }
}

export function hasRememberedPrivacyConsent() {
  return read(PRIVACY_CONSENT_KEY) === "true";
}

export function rememberPrivacyConsent(granted) {
  write(PRIVACY_CONSENT_KEY, granted ? "true" : "");
}

export function getRecentAvatarUrl() {
  return read(RECENT_AVATAR_KEY) || "";
}

export function rememberRecentAvatar(url) {
  write(RECENT_AVATAR_KEY, String(url || "").trim());
}
