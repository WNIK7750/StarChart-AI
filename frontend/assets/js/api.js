const API_BASE = window.API_BASE || "/api/v1";

function buildApiUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  if (path.startsWith(API_BASE)) return path;
  return `${API_BASE}${path}`;
}

function authHeaders() {
  const token = localStorage.getItem("ai_nav_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiRequest(path, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail || data.message || `API ${response.status}: ${path}`;
    throw new Error(message);
  }
  return data;
}

export async function apiGet(path, params = {}) {
  const url = new URL(buildApiUrl(path), window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return apiRequest(url.pathname + url.search);
}

export async function apiPost(path, body = {}) {
  return apiRequest(path, { method: "POST", body: JSON.stringify(body) });
}

export async function apiPut(path, body = {}) {
  return apiRequest(path, { method: "PUT", body: JSON.stringify(body) });
}

export async function apiPatch(path, body = {}) {
  return apiRequest(path, { method: "PATCH", body: JSON.stringify(body) });
}

export async function apiDelete(path) {
  return apiRequest(path, { method: "DELETE" });
}

export async function apiUpload(path, formData) {
  const response = await fetch(buildApiUrl(path), {
    method: "POST",
    headers: {
      ...authHeaders(),
    },
    body: formData,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.detail || data.message || `API ${response.status}: ${path}`;
    throw new Error(message);
  }
  return data;
}

export function saveAuthTokens(data) {
  if (data.accessToken) localStorage.setItem("ai_nav_access_token", data.accessToken);
  if (data.refreshToken) localStorage.setItem("ai_nav_refresh_token", data.refreshToken);
}

export function clearAuthTokens() {
  localStorage.removeItem("ai_nav_access_token");
  localStorage.removeItem("ai_nav_refresh_token");
}

export function getRefreshToken() {
  return localStorage.getItem("ai_nav_refresh_token") || "";
}

export function getAccessToken() {
  return localStorage.getItem("ai_nav_access_token") || "";
}
