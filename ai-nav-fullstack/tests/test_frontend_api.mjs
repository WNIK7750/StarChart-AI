import assert from "node:assert/strict";
import test from "node:test";

const storage = new Map();
globalThis.window = {
  API_BASE: "/api/v1",
  location: { origin: "http://localhost" },
  setTimeout,
  clearTimeout,
};
globalThis.localStorage = {
  getItem: (key) => storage.get(key) || null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
};
const { ApiError, apiGet, apiPost } = await import(`../frontend/assets/js/api.js?test=${Date.now()}`);

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
  storage.set("ai_nav_access_token", "valid-access-token");
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
