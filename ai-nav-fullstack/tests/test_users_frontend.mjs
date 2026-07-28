import assert from "node:assert/strict";
import fs from "node:fs";

const settingsScript = fs.readFileSync("frontend/assets/js/settings.js", "utf8");
const settingsHtml = fs.readFileSync("frontend/settings.html", "utf8");
assert.match(settingsScript, /new URLSearchParams\(window\.location\.search\)\.get\("workflow"\)/);
assert.match(settingsScript, /data-workflow-uid/);
assert.match(settingsScript, /target\.focus\(\{ preventScroll: true \}\)/);
assert.match(settingsScript, /target\.scrollIntoView/);
assert.match(settingsScript, /data-workflow-detail-toggle/);
assert.match(settingsScript, /workflowStepsMarkup\(item\)/);
assert.match(settingsScript, /aria-expanded/);
assert.match(settingsScript, /safeInternalHref\(step\.target\?\.href, ""\)/);
assert.match(settingsHtml, /\.learning-item\.workflow-target/);
assert.match(settingsHtml, /\.learning-item\.workflow-target:focus-visible\{outline:2px solid #5f6668/);
assert.match(settingsHtml, /\.workflow-detail-region\{grid-column:1\/-1\}/);
assert.match(settingsHtml, /\.learning-item \.workflow-step-number\{[^}]*display:inline-flex;align-items:center;justify-content:center;[^}]*margin:0;[^}]*line-height:1/);
assert.match(settingsHtml, /核对 Agent 保存的工作流步骤与工具状态/);

const storage = new Map([["ai_nav_access_token", "test-access-token"]]);
globalThis.window = {
  AI_NAV_PUBLIC_BASE_PATH: "/StarChart-AI",
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
const { getAccessToken, saveAuthTokens } = await import("../frontend/assets/js/api.js");
saveAuthTokens({ accessToken: "test-access-token" });

await users.getCurrentUser();
await users.updateUserProfile({ expectedVersion: 3, displayName: "Alice" });
await users.revokeUserSession("session with space");
await users.getUserPreferenceContext("learning");
await users.logoutUser();
await users.getUserPrivacyConsents();
await users.updateUserPrivacyConsent("agent_memory", { policyVersion: "2026-07-01", granted: true });
await users.exportUserData("Current123");
await users.requestUserDeletion({ currentPassword: "Current123", reasonCode: "unused" });
await users.cancelUserDeletion("datareq with space");
await users.listUserWorkflows({ status: "active", page: 2, pageSize: 10 });
await users.archiveUserWorkflow("workflow with space", 4);
await users.restoreUserWorkflow("workflow with space", 5);
await users.saveAgentWorkflow(
  { confirmed: true, sourceType: "agent", title: "Research workflow", steps: [] },
  "agent-save-001",
);
await users.uploadUserAvatar(new FormData());

assert.equal(requests[0].url, "/StarChart-AI/api/v1/auth/me");
assert.equal(requests[0].options.headers.Authorization, "Bearer " + "test-access-token");
assert.equal(requests[1].url, "/StarChart-AI/api/v1/users/me/profile");
assert.equal(requests[1].options.method, "PATCH");
assert.deepEqual(JSON.parse(requests[1].options.body), { expectedVersion: 3, displayName: "Alice" });
assert.equal(requests[2].url, "/StarChart-AI/api/v1/users/me/sessions/session%20with%20space");
assert.equal(requests[2].options.method, "DELETE");
assert.equal(requests[3].url, "/StarChart-AI/api/v1/users/me/preferences/context?consumer=learning");
assert.equal(requests[4].url, "/StarChart-AI/api/v1/auth/logout");
assert.equal(requests[4].options.credentials, "same-origin");
assert.equal(requests[5].url, "/StarChart-AI/api/v1/users/me/privacy/consents");
assert.equal(requests[6].url, "/StarChart-AI/api/v1/users/me/privacy/consents/agent_memory");
assert.equal(requests[6].options.method, "PUT");
assert.deepEqual(JSON.parse(requests[6].options.body), { policyVersion: "2026-07-01", granted: true });
assert.equal(requests[7].url, "/StarChart-AI/api/v1/users/me/privacy/export");
assert.deepEqual(JSON.parse(requests[7].options.body), { currentPassword: "Current123" });
assert.equal(requests[8].url, "/StarChart-AI/api/v1/users/me/privacy/deletion-requests");
assert.equal(requests[9].url, "/StarChart-AI/api/v1/users/me/privacy/deletion-requests/datareq%20with%20space");
assert.equal(requests[9].options.method, "DELETE");
assert.equal(requests[10].url, "/StarChart-AI/api/v1/users/me/assets/workflows?status=active&page=2&pageSize=10");
assert.equal(requests[11].url, "/StarChart-AI/api/v1/users/me/assets/workflows/workflow%20with%20space/archive");
assert.deepEqual(JSON.parse(requests[11].options.body), { expectedVersion: 4 });
assert.equal(requests[12].url, "/StarChart-AI/api/v1/users/me/assets/workflows/workflow%20with%20space/restore");
assert.deepEqual(JSON.parse(requests[12].options.body), { expectedVersion: 5 });
assert.equal(requests[13].url, "/StarChart-AI/api/v1/agent/workflows/save");
assert.equal(requests[13].options.headers["Idempotency-Key"], "agent-save-001");
assert.equal(JSON.parse(requests[13].options.body).confirmed, true);
assert.equal(requests[14].url, "/StarChart-AI/api/v1/users/me/avatar");
assert.equal(requests[14].options.method, "POST");

saveAuthTokens({ accessToken: "expired-access-token" });
let protectedCalls = 0;
let refreshCalls = 0;
globalThis.fetch = async (url, options = {}) => {
  if (url === "/StarChart-AI/api/v1/auth/refresh") {
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
  if (url === "/StarChart-AI/api/v1/auth/me") {
    protectedCalls += 1;
    const renewed = options.headers.Authorization === "Bearer " + "renewed-access-token";
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
assert.equal(getAccessToken(), "renewed-access-token");
assert.equal(storage.has("ai_nav_access_token"), false);
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

const settings = await import(`../frontend/assets/js/settings.js?test=${Date.now()}`);
assert.equal(
  settings.projectAvatarUrl("/uploads/avatars/user.webp"),
  "/StarChart-AI/uploads/avatars/user.webp",
);
assert.deepEqual(
  settings.publicSettingsVisibility({
    auth: {
      identityChanges: false,
      recovery: false,
      privacyWrites: false,
    },
  }),
  {
    identityChanges: false,
    passwordChanges: false,
    recovery: false,
    privacyWrites: false,
  },
);
const element = () => ({ hidden: false, disabled: false });
const accountSection = element();
const accountLink = element();
const securitySection = element();
const securityLink = element();
const passwordPanel = element();
const recoveryPanel = element();
const privacyLabel = element();
const privacyInput = {
  ...element(),
  closest: () => privacyLabel,
};
const agentMemoryLabel = element();
const agentMemoryInput = {
  ...element(),
  closest: () => agentMemoryLabel,
};
const deletionForm = element();
const cancelDeletion = element();
const availableSections = ["profile", "sessions", "preferences", "workflows"]
  .map((name) => [`[data-section="${name}"]`, element()]);
const capabilityElements = new Map([
  ['[data-section="account"]', accountSection],
  ['[data-section-link][href="#account"]', accountLink],
  ['[data-section="security"]', securitySection],
  ['[data-section-link][href="#security"]', securityLink],
  ["[data-password-form]", { closest: () => passwordPanel }],
  ["[data-security-form]", { closest: () => recoveryPanel }],
  ["[data-privacy-consent-form] [name='privacyPolicy']", privacyInput],
  ["[data-preferences-form] [name='agentMemoryEnabled']", agentMemoryInput],
  ["[data-deletion-form]", deletionForm],
  ...availableSections,
]);
const capabilityRoot = {
  querySelector: (selector) => capabilityElements.get(selector) ?? null,
  querySelectorAll: (selector) => selector === "[data-cancel-deletion]" ? [cancelDeletion] : [],
};
settings.applyPublicSettingsCapabilities(null, capabilityRoot);
for (const restricted of [
  accountSection,
  accountLink,
  securitySection,
  securityLink,
  passwordPanel,
  recoveryPanel,
  privacyLabel,
  agentMemoryLabel,
  deletionForm,
  cancelDeletion,
]) {
  assert.equal(restricted.hidden, true);
}
assert.equal(privacyInput.disabled, true);
assert.equal(agentMemoryInput.disabled, true);
assert.equal(deletionForm.disabled, true);
assert.equal(cancelDeletion.disabled, true);
for (const [, available] of availableSections) assert.equal(available.hidden, false);

settings.applyPublicSettingsCapabilities({
  auth: {
    identityChanges: true,
    recovery: true,
    privacyWrites: true,
  },
}, capabilityRoot);
assert.equal(deletionForm.hidden, false);
assert.equal(deletionForm.disabled, false);
assert.equal(cancelDeletion.hidden, false);
assert.equal(cancelDeletion.disabled, false);

console.log("users frontend facade tests passed");
