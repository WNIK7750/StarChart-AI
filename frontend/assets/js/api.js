const API_BASE = window.API_BASE || "/api/v1";
const DEFAULT_TIMEOUT_MS = 10000;
const RETRYABLE_STATUS = new Set([502, 503, 504]);
const REFRESHABLE_AUTH_CODES = new Set(["AUTH_TOKEN_INVALID", "AUTH_TOKEN_EXPIRED"]);

export class ApiError extends Error {
  constructor(message, { status, code, payload, path } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.payload = payload;
    this.path = path;
  }
}

function buildApiUrl(path) {
  if (/^https?:\/\//.test(path)) return path;
  if (path.startsWith(API_BASE)) return path;
  return `${API_BASE}${path}`;
}

function authHeaders() {
  const token = localStorage.getItem("ai_nav_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

let refreshInFlight = null;

function requestDeadline(externalSignal, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => controller.abort(externalSignal?.reason);
  if (externalSignal?.aborted) abortFromCaller();
  else externalSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timer = globalThis.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  return {
    signal: controller.signal,
    timedOut: () => timedOut,
    cleanup() {
      globalThis.clearTimeout(timer);
      externalSignal?.removeEventListener("abort", abortFromCaller);
    },
  };
}

function requestFailure(error, path, timedOut, externalSignal) {
  if (error instanceof ApiError) return error;
  if (timedOut) return new ApiError("请求超时，请稍后重试", { status: 0, code: "API_TIMEOUT", path });
  if (externalSignal?.aborted) return new ApiError("请求已取消", { status: 0, code: "API_REQUEST_ABORTED", path });
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return new ApiError("当前处于离线状态", { status: 0, code: "API_OFFLINE", path });
  }
  return new ApiError("网络连接失败，请稍后重试", { status: 0, code: "API_NETWORK_ERROR", path });
}

async function fetchWithDeadline(path, options, timeoutMs) {
  const deadline = requestDeadline(options.signal, timeoutMs);
  try {
    return await fetch(buildApiUrl(path), { ...options, signal: deadline.signal });
  } catch (error) {
    throw requestFailure(error, path, deadline.timedOut(), options.signal);
  } finally {
    deadline.cleanup();
  }
}

function shouldRefresh(path) {
  if (!getAccessToken()) return false;
  const pathname = new URL(buildApiUrl(path), window.location.origin).pathname;
  return ![
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/auth/username-available",
  ].some((excluded) => pathname === excluded || pathname.startsWith("/api/v1/auth/password-reset/"));
}

function isRefreshableAuthFailure(response, data) {
  return response.status === 401 && REFRESHABLE_AUTH_CODES.has(data.detail?.code);
}

async function refreshAccessToken() {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const response = await fetchWithDeadline("/auth/refresh", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      }, DEFAULT_TIMEOUT_MS);
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.accessToken) {
        const message = data.detail?.message || data.detail || "登录已失效";
        throw new ApiError(String(message), {
          status: response.status,
          code: data.detail?.code,
          payload: data,
          path: "/auth/refresh",
        });
      }
      saveAuthTokens(data);
      return data.accessToken;
    })()
      .catch((error) => {
        clearAuthTokens();
        throw error;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function apiRequest(path, options = {}, allowRefresh = true) {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retryCount = 0,
    signal,
    ...fetchOptions
  } = options;
  let response;
  try {
    response = await fetchWithDeadline(path, {
      ...fetchOptions,
      signal,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(fetchOptions.headers || {}),
      },
    }, timeoutMs);
  } catch (error) {
    if (retryCount > 0 && error.code === "API_NETWORK_ERROR") {
      return apiRequest(path, { ...options, retryCount: retryCount - 1 }, allowRefresh);
    }
    throw error;
  }
  if (retryCount > 0 && RETRYABLE_STATUS.has(response.status)) {
    return apiRequest(path, { ...options, retryCount: retryCount - 1 }, allowRefresh);
  }
  const data = await response.json().catch(() => ({}));
  if (isRefreshableAuthFailure(response, data) && allowRefresh && shouldRefresh(path)) {
    await refreshAccessToken();
    return apiRequest(path, options, false);
  }
  if (!response.ok) {
    const message = data.detail?.message || data.detail || data.message || `API ${response.status}: ${path}`;
    throw new ApiError(String(message), { status: response.status, code: data.detail?.code, payload: data, path });
  }
  return data;
}

export async function apiGet(path, params = {}, options = {}) {
  const url = new URL(buildApiUrl(path), window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return apiRequest(url.pathname + url.search, {
    ...options,
    method: "GET",
    retryCount: options.retryCount ?? 1,
  });
}

export async function apiPost(path, body = {}, options = {}) {
  return apiRequest(path, { ...options, method: "POST", body: JSON.stringify(body) });
}

export async function apiPut(path, body = {}, options = {}) {
  return apiRequest(path, { ...options, method: "PUT", body: JSON.stringify(body) });
}

export async function apiPatch(path, body = {}, options = {}) {
  return apiRequest(path, { ...options, method: "PATCH", body: JSON.stringify(body) });
}

export async function apiDelete(path, options = {}) {
  return apiRequest(path, { ...options, method: "DELETE" });
}

export async function apiUpload(path, formData, options = {}) {
  return uploadRequest(path, formData, options, true);
}

async function uploadRequest(path, formData, options, allowRefresh) {
  const response = await fetchWithDeadline(path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      ...authHeaders(),
      ...(options.headers || {}),
    },
    body: formData,
    signal: options.signal,
  }, options.timeoutMs || DEFAULT_TIMEOUT_MS);
  const data = await response.json().catch(() => ({}));
  if (isRefreshableAuthFailure(response, data) && allowRefresh && shouldRefresh(path)) {
    await refreshAccessToken();
    return uploadRequest(path, formData, options, false);
  }
  if (!response.ok) {
    const message = data.detail?.message || data.detail || data.message || `API ${response.status}: ${path}`;
    throw new ApiError(String(message), { status: response.status, code: data.detail?.code, payload: data, path });
  }
  return data;
}

export function saveAuthTokens(data) {
  if (data.accessToken) localStorage.setItem("ai_nav_access_token", data.accessToken);
  if (data.refreshToken) localStorage.removeItem("ai_nav_refresh_token");
}

export function clearAuthTokens() {
  localStorage.removeItem("ai_nav_access_token");
  localStorage.removeItem("ai_nav_refresh_token");
}

export function getRefreshToken() {
  // Compatibility for sessions created before HttpOnly refresh cookies.
  return localStorage.getItem("ai_nav_refresh_token") || "";
}

export function getAccessToken() {
  return localStorage.getItem("ai_nav_access_token") || "";
}
