import assert from "node:assert/strict";

const storage = new Map([["ai_nav_access_token", "test-access-token"]]);
globalThis.window = {
  API_BASE: "/api/v1",
  location: { origin: "http://localhost" },
  localStorage: {
    getItem: (key) => storage.get(key) || null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  },
};
globalThis.localStorage = globalThis.window.localStorage;

const requests = [];
globalThis.fetch = async (url, options = {}) => {
  requests.push({ url, options });
  return { ok: true, json: async () => ({ ok: true }) };
};

const users = await import("../frontend/assets/js/users-api.js");

await users.getCurrentUser();
await users.updateUserProfile({ expectedVersion: 3, displayName: "Alice" });
await users.revokeUserSession("session/with space");
await users.getUserPreferenceContext("learning");
await users.logoutUser();
await users.getUserPrivacyConsents();
await users.updateUserPrivacyConsent("agent_memory", { policyVersion: "2026-07-01", granted: true });
await users.exportUserData("Current123");
await users.requestUserDeletion({ currentPassword: "Current123", reasonCode: "unused" });
await users.cancelUserDeletion("datareq/with space");
await users.listUserWorkflows({ status: "active", page: 2, pageSize: 10 });
await users.archiveUserWorkflow("workflow/with space", 4);
await users.restoreUserWorkflow("workflow/with space", 5);
await users.saveAgentWorkflow(
  { confirmed: true, sourceType: "agent", title: "Research workflow", steps: [] },
  "agent-save-001",
);

assert.equal(requests[0].url, "/api/v1/auth/me");
assert.equal(requests[0].options.headers.Authorization, "Bearer test-access-token");
assert.equal(requests[1].url, "/api/v1/users/me/profile");
assert.equal(requests[1].options.method, "PATCH");
assert.deepEqual(JSON.parse(requests[1].options.body), { expectedVersion: 3, displayName: "Alice" });
assert.equal(requests[2].url, "/api/v1/users/me/sessions/session%2Fwith%20space");
assert.equal(requests[2].options.method, "DELETE");
assert.equal(requests[3].url, "/api/v1/users/me/preferences/context?consumer=learning");
assert.equal(requests[4].url, "/api/v1/auth/logout");
assert.equal(requests[4].options.credentials, "same-origin");
assert.equal(requests[5].url, "/api/v1/users/me/privacy/consents");
assert.equal(requests[6].url, "/api/v1/users/me/privacy/consents/agent_memory");
assert.equal(requests[6].options.method, "PUT");
assert.deepEqual(JSON.parse(requests[6].options.body), { policyVersion: "2026-07-01", granted: true });
assert.equal(requests[7].url, "/api/v1/users/me/privacy/export");
assert.deepEqual(JSON.parse(requests[7].options.body), { currentPassword: "Current123" });
assert.equal(requests[8].url, "/api/v1/users/me/privacy/deletion-requests");
assert.equal(requests[9].url, "/api/v1/users/me/privacy/deletion-requests/datareq%2Fwith%20space");
assert.equal(requests[9].options.method, "DELETE");
assert.equal(requests[10].url, "/api/v1/users/me/assets/workflows?status=active&page=2&pageSize=10");
assert.equal(requests[11].url, "/api/v1/users/me/assets/workflows/workflow%2Fwith%20space/archive");
assert.deepEqual(JSON.parse(requests[11].options.body), { expectedVersion: 4 });
assert.equal(requests[12].url, "/api/v1/users/me/assets/workflows/workflow%2Fwith%20space/restore");
assert.deepEqual(JSON.parse(requests[12].options.body), { expectedVersion: 5 });
assert.equal(requests[13].url, "/api/v1/agent/workflows/save");
assert.equal(requests[13].options.headers["Idempotency-Key"], "agent-save-001");
assert.equal(JSON.parse(requests[13].options.body).confirmed, true);

storage.set("ai_nav_access_token", "expired-access-token");
let protectedCalls = 0;
let refreshCalls = 0;
globalThis.fetch = async (url, options = {}) => {
  if (url === "/api/v1/auth/refresh") {
    refreshCalls += 1;
    assert.equal(options.credentials, "same-origin");
    assert.equal(options.headers.Authorization, undefined);
    await new Promise((resolve) => setTimeout(resolve, 5));
    return {
      ok: true,
      status: 200,
      json: async () => ({ accessToken: "renewed-access-token", tokenType: "Bearer", expiresIn: 1800 }),
    };
  }
  if (url === "/api/v1/auth/me") {
    protectedCalls += 1;
    const renewed = options.headers.Authorization === "Bearer renewed-access-token";
    return {
      ok: renewed,
      status: renewed ? 200 : 401,
      json: async () => renewed
        ? ({ user: { userUid: "usr_refresh" } })
        : ({ detail: { code: "AUTH_TOKEN_INVALID", message: "expired" } }),
    };
  }
  throw new Error(`unexpected request ${url}`);
};
const refreshedUsers = await Promise.all([users.getCurrentUser(), users.getCurrentUser()]);
assert.equal(refreshCalls, 1);
assert.equal(protectedCalls, 4);
assert.equal(storage.get("ai_nav_access_token"), "renewed-access-token");
assert.deepEqual(refreshedUsers.map((item) => item.user.userUid), ["usr_refresh", "usr_refresh"]);

const consumers = await import("../frontend/assets/js/user-preference-consumers.js");
const resources = [
  { title: "External", accessType: "external" },
  { title: "Domestic", accessType: "cn" },
  { title: "Neutral", accessType: "neutral" },
];
assert.deepEqual(
  consumers.applyLearningResourcePreferences(resources, { cnFirst: true, showExternalResources: false }).map((item) => item.title),
  ["Domestic", "Neutral"],
);
assert.deepEqual(resources.map((item) => item.title), ["External", "Domestic", "Neutral"]);

const tools = [
  { name: "Paid", tags: ["商用"] },
  { name: "Free", tags: ["免费", "开发"] },
];
assert.deepEqual(
  consumers.applyToolPreferences(tools, { freeFirst: true }).map((item) => item.name),
  ["Free", "Paid"],
);

console.log("users frontend facade tests passed");
