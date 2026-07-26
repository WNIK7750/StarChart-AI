import assert from "node:assert/strict";
import test from "node:test";

const storage = new Map();
const authEvents = [];
globalThis.window = {
  AI_NAV_PUBLIC_BASE_PATH: "/StarChart-AI",
  location: { origin: "http://localhost" },
  dispatchEvent: (event) => authEvents.push(event),
  setTimeout,
  clearTimeout,
};
globalThis.localStorage = {
  getItem: (key) => storage.get(key) || null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
};
const {
  API_BASE,
  ApiError,
  apiGet,
  apiPost,
  apiPostStream,
  clearAuthTokens,
  getAccessToken,
  restoreAuthSession,
  saveAuthTokens,
} = await import(`../frontend/assets/js/api.js?test=${Date.now()}`);

test("all API requests share the deployment-prefixed API base", async () => {
  assert.equal(API_BASE, "/StarChart-AI/api/v1");
  let captured;
  globalThis.fetch = async (url) => {
    captured = url;
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  await apiPost("/auth/login", {});
  assert.equal(captured, `${API_BASE}/auth/login`);
});

test("access tokens stay in memory and legacy storage is removed", () => {
  storage.set("ai_nav_access_token", "legacy-access");
  storage.set("ai_nav_refresh_token", "legacy-refresh");
  saveAuthTokens({ accessToken: "memory-access", refreshToken: "must-not-persist" });
  assert.deepEqual(authEvents.at(-1).detail, { authenticated: true });
  assert.equal(getAccessToken(), "memory-access");
  assert.equal(storage.has("ai_nav_access_token"), false);
  assert.equal(storage.has("ai_nav_refresh_token"), false);
  clearAuthTokens();
  assert.deepEqual(authEvents.at(-1).detail, { authenticated: false });
  assert.equal(getAccessToken(), "");
});

test("page reload authentication is restored through the refresh cookie flow", async () => {
  clearAuthTokens();
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({
      accessToken: "restored-access",
      tokenType: "Bearer",
      expiresIn: 600,
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  assert.equal(await restoreAuthSession(), "restored-access");
  assert.equal(captured.url, `${API_BASE}/auth/refresh`);
  assert.equal(captured.options.credentials, "same-origin");
  assert.equal(storage.has("ai_nav_access_token"), false);
});

test("GET retries one transient network failure", async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    if (calls === 1) throw new TypeError("network down");
    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  assert.deepEqual(await apiGet("/health"), { ok: true });
  assert.equal(calls, 2);
});

test("write requests are never retried automatically", async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    throw new TypeError("network down");
  };
  await assert.rejects(apiPost("/write", { value: 1 }), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.code, "API_NETWORK_ERROR");
    return true;
  });
  assert.equal(calls, 1);
});

test("business 401 responses do not refresh or replay writes", async () => {
  saveAuthTokens({ accessToken: "valid-access-token" });
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return new Response(JSON.stringify({
      detail: { code: "CURRENT_PASSWORD_INVALID", message: "current password required" },
    }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  };
  await assert.rejects(apiPost("/users/me/account", { email: "new@example.test" }), (error) => {
    assert.equal(error.code, "CURRENT_PASSWORD_INVALID");
    return true;
  });
  assert.equal(calls, 1);
});

test("timeout and caller cancellation have different stable codes", async () => {
  globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
  });
  await assert.rejects(apiGet("/slow", {}, { timeoutMs: 5, retryCount: 0 }), (error) => {
    assert.equal(error.code, "API_TIMEOUT");
    return true;
  });

  const controller = new AbortController();
  const request = apiGet("/cancel", {}, { signal: controller.signal, timeoutMs: 100, retryCount: 0 });
  controller.abort();
  await assert.rejects(request, (error) => {
    assert.equal(error.code, "API_REQUEST_ABORTED");
    return true;
  });
});

test("stream requests keep auth server-side and require an SSE response", async () => {
  saveAuthTokens({ accessToken: "stream-access-token" });
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response("event: response.started\ndata: {}\n\n", {
      status: 200,
      headers: { "Content-Type": "text/event-stream; charset=utf-8" },
    });
  };
  const response = await apiPostStream("/agent/chat/stream", { message: "RAG" });
  assert.equal(response.status, 200);
  assert.equal(captured.options.headers.Authorization, "Bearer stream-access-token");
  assert.equal(captured.options.headers.Accept, "text/event-stream");
  assert.equal(captured.url, `${API_BASE}/agent/chat/stream`);

  globalThis.fetch = async () => new Response("{}", {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
  await assert.rejects(apiPostStream("/agent/chat/stream", {}), (error) => {
    assert.equal(error.code, "API_STREAM_CONTENT_TYPE_INVALID");
    return true;
  });
});
