import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

function accessToken(subject, nonce) {
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${encode({ alg: "none" })}.${encode({ sub: subject, nonce })}.signature`;
}

function deferred() {
  let resolve;
  const promise = new Promise((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

async function applyCurrentOperation(epoch, pending, apply, onStart = null) {
  const operation = epoch.beginOperation();
  onStart?.(operation);
  try {
    const result = await pending;
    if (!operation.isCurrent()) return;
    apply(result);
  } finally {
    operation.finish();
  }
}

test("login dialog uses the site logo until a recent account avatar exists", () => {
  const source = read("frontend/assets/js/auth-ui.js");
  assert.match(
    source,
    /DEFAULT_AUTH_AVATAR = withPublicBasePath\("\/assets\/img\/brand-mark\.[a-f0-9]{8}\.svg"\)/,
  );
  assert.doesNotMatch(source, /assets\/img\/logo\.png/);
  assert.match(source, /data-auth-avatar/);
  assert.match(source, /getRecentAvatarUrl\(\)/);
  assert.match(source, /rememberRecentAvatar\(avatarUrl\)/);
  assert.match(source, /input\[type=\"password\"\]/);
  assert.match(source, /name="phone" type="tel" autocomplete="tel"/);
  assert.match(source, /if \(mode === "login"\) body\.rememberMe/);
});

test("auth bootstrap binds immediately and starts independent network work together", () => {
  const source = read("frontend/assets/js/auth-ui.js");
  assert.match(source, /let authInitializationPromise = null/);
  assert.match(source, /let authRefreshVersion = 0/);
  assert.match(source, /refreshVersion !== authRefreshVersion/);
  assert.match(source, /function bindAuthEvents\(\)/);
  assert.match(source, /if \(authInitializationPromise\) return authInitializationPromise/);
  assert.match(
    source,
    /Promise\.all\(\[\s*loadPublicAuthCapabilities\(\),\s*refreshAuthUI\(\),?\s*\]\)/,
  );
  const init = source.match(/export function initAuthUI\(\) \{([\s\S]*?)\n\}/)?.[1] || "";
  assert.ok(
    init.indexOf("bindAuthEvents()") < init.indexOf("Promise.all"),
    "auth controls must be interactive before network hydration",
  );
});

test("successful login invalidates an older bootstrap refresh before any further await", () => {
  const source = read("frontend/assets/js/auth-ui.js");
  const handler = source.match(
    /async function handleLoginOrRegister\(form, mode\) \{([\s\S]*?)\n\}/,
  )?.[1] || "";
  const savedAt = handler.indexOf("saveAuthTokens(data)");
  const refreshedAt = handler.indexOf("const authenticatedRefresh = refreshAuthUI()");
  const importAt = handler.indexOf('await import("./anonymous-learning-state.js")');
  assert.ok(savedAt >= 0, "login must save the new access token");
  assert.ok(refreshedAt > savedAt, "login must invalidate the bootstrap refresh after saving");
  assert.ok(importAt > refreshedAt, "no awaited follow-up may leave the old refresh current");
  assert.match(handler, /return authenticatedRefresh/);
});

test("account settings expose email and phone binding with password confirmation", () => {
  const settings = read("frontend/settings.html");
  assert.match(settings, /data-account-form/);
  assert.match(settings, /name="email" type="email" autocomplete="email"/);
  assert.match(settings, /name="phone" type="tel" autocomplete="tel"/);
  assert.match(settings, /name="currentPassword" type="password"/);
  assert.match(settings, /修改邮箱或手机号时必须填写/);
});

test("auth local state stores only consent and avatar URL preferences", async () => {
  const values = new Map();
  globalThis.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key),
    },
  };
  const moduleUrl = pathToFileURL(path.join(root, "frontend/assets/js/auth-local-state.js"));
  const state = await import(`${moduleUrl.href}?test=${Date.now()}`);
  state.rememberPrivacyConsent(true);
  state.rememberRecentAvatar("/uploads/avatars/alice.webp");
  assert.equal(state.hasRememberedPrivacyConsent(), true);
  assert.equal(state.getRecentAvatarUrl(), "/uploads/avatars/alice.webp");
  assert.deepEqual([...values.keys()].sort(), ["ai_nav_privacy_consent_2026-07-20", "ai_nav_recent_avatar_v1"]);
  assert.doesNotMatch(JSON.stringify([...values]), /password|token/i);
  delete globalThis.window;
});

test("login and settings dialogs expose the current detailed policy", () => {
  const auth = read("frontend/assets/js/auth-ui.js");
  const settings = read("frontend/settings.html");
  for (const source of [auth, settings]) {
    assert.match(source, /版本：2026-07-20/);
    assert.match(source, /不出售个人信息/);
    assert.match(source, /阿里云百炼千问/);
    assert.match(source, /不会发送账号资料、用户资产或长期记忆/);
    assert.match(source, /导出数据/);
    assert.match(source, /撤回/);
  }
});

test("password recovery uses an external one-time credential instead of security answers", () => {
  const auth = read("frontend/assets/js/auth-ui.js");
  const api = read("frontend/assets/js/users-api.js");
  assert.match(auth, /账号已验证的外部恢复通道/);
  assert.match(auth, /name="resetToken" autocomplete="one-time-code"/);
  assert.doesNotMatch(auth, /data-reset-questions|data-answer|提交答案/);
  assert.match(api, /password-reset\/start/);
  assert.match(api, /password-reset\/confirm/);
  assert.doesNotMatch(api, /password-reset\/security\/verify/);
});

test("http-test auth capabilities conservatively hide registration and recovery", async () => {
  const values = new Map();
  globalThis.window = {
    AI_NAV_PUBLIC_BASE_PATH: "/StarChart-AI",
    location: { origin: "http://localhost" },
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key),
    },
  };
  globalThis.localStorage = globalThis.window.localStorage;
  const moduleUrl = pathToFileURL(path.join(root, "frontend/assets/js/auth-ui.js"));
  const auth = await import(`${moduleUrl.href}?capabilities=${Date.now()}`);

  assert.deepEqual(
    auth.publicAuthEntryVisibility({
      auth: { registration: false, recovery: false },
    }),
    { registration: false, recovery: false },
  );
  assert.deepEqual(
    auth.publicAuthEntryVisibility(null),
    { registration: false, recovery: false },
  );
  const registerTab = { hidden: false };
  const registerForm = { hidden: false };
  const resetEntries = [{ hidden: false }, { hidden: false }];
  const resetForms = [{ hidden: false }, { hidden: false }];
  const panel = {
    querySelector: (selector) => ({
      '[data-auth-tab="register"]': registerTab,
      '[data-auth-form="register"]': registerForm,
      "[data-auth-form].active": null,
    })[selector] ?? null,
    querySelectorAll: (selector) => ({
      '[data-auth-tab^="reset"]': resetEntries,
      '[data-auth-form^="reset"]': resetForms,
    })[selector] ?? [],
  };
  auth.applyPublicAuthCapabilities(null, panel);
  assert.equal(registerTab.hidden, true);
  assert.equal(registerForm.hidden, true);
  assert.deepEqual(resetEntries.map((entry) => entry.hidden), [true, true]);
  assert.deepEqual(resetForms.map((entry) => entry.hidden), [true, true]);
  delete globalThis.localStorage;
  delete globalThis.window;
});

test("assistant identity changes preserve the isolated guest-memory boundary", () => {
  const assistant = read("frontend/assets/js/assistant-page.js");
  assert.match(assistant, /getAccessToken\(\)/);
  assert.match(assistant, /new AssistantSessionEpoch\(getAccessToken\(\)\)/);
  assert.match(assistant, /sessionEpoch\.beginOperation\(\)/);
  assert.match(assistant, /window\.addEventListener\("ai-nav-auth-changed"/);
  assert.match(assistant, /renderGuestConversation/);
  assert.doesNotMatch(assistant, /importGuest|migrateGuest|syncGuest/);
  const authChangeHandler = assistant.match(
    /window\.addEventListener\("ai-nav-auth-changed", \(\) => \{([\s\S]*?)\n\}\);/,
  )?.[1] || "";
  assert.doesNotMatch(authChangeHandler, /clearGuestConversations|appendGuestMessage|recentGuestHistory/);
});

test("assistant session list and detail completions cannot render after identity transitions", async () => {
  const moduleUrl = pathToFileURL(
    path.join(root, "frontend/assets/js/assistant-session-epoch.js"),
  );
  const { AssistantSessionEpoch } = await import(`${moduleUrl.href}?test=${Date.now()}`);
  const alice = accessToken("usr_alice", "first");
  const bob = accessToken("usr_bob", "first");
  const epoch = new AssistantSessionEpoch(alice);
  const pendingList = deferred();
  const pendingDetail = deferred();
  const rendered = { titles: [], messages: [] };
  let listSignal;
  let detailSignal;

  const listCompletion = applyCurrentOperation(epoch, pendingList.promise, (items) => {
    rendered.titles = items;
  }, (operation) => { listSignal = operation.signal; });
  epoch.transition("");
  assert.equal(listSignal.aborted, true);
  pendingList.resolve(["Alice private session"]);
  await listCompletion;

  epoch.transition(alice);
  const detailCompletion = applyCurrentOperation(epoch, pendingDetail.promise, (items) => {
    rendered.messages = items;
  }, (operation) => { detailSignal = operation.signal; });
  epoch.transition(bob);
  assert.equal(detailSignal.aborted, true);
  pendingDetail.resolve(["Alice private message"]);
  await detailCompletion;

  assert.deepEqual(rendered, { titles: [], messages: [] });
});

test("assistant session mutations cannot update guest or another user after transition", async () => {
  const moduleUrl = pathToFileURL(
    path.join(root, "frontend/assets/js/assistant-session-epoch.js"),
  );
  const { AssistantSessionEpoch } = await import(`${moduleUrl.href}?test=${Date.now()}`);
  const epoch = new AssistantSessionEpoch(accessToken("usr_alice", "first"));
  const pendingCreate = deferred();
  const state = { currentSessionId: "guest-session" };
  let mutationSignal;

  const completion = applyCurrentOperation(epoch, pendingCreate.promise, (sessionId) => {
    state.currentSessionId = sessionId;
  }, (operation) => { mutationSignal = operation.signal; });
  epoch.transition(accessToken("usr_bob", "first"));
  assert.equal(mutationSignal.aborted, true);
  pendingCreate.resolve("alice-server-session");
  await completion;

  assert.equal(state.currentSessionId, "guest-session");
});

test("assistant same-user token refresh keeps the current session operation valid", async () => {
  const moduleUrl = pathToFileURL(
    path.join(root, "frontend/assets/js/assistant-session-epoch.js"),
  );
  const { AssistantSessionEpoch } = await import(`${moduleUrl.href}?test=${Date.now()}`);
  const epoch = new AssistantSessionEpoch(accessToken("usr_alice", "first"));
  const pendingList = deferred();
  const rendered = [];
  let refreshSignal;

  const completion = applyCurrentOperation(epoch, pendingList.promise, (items) => {
    rendered.push(...items);
  }, (operation) => { refreshSignal = operation.signal; });
  const changed = epoch.transition(accessToken("usr_alice", "refreshed"));
  assert.equal(refreshSignal.aborted, false);
  pendingList.resolve(["Alice current session"]);
  await completion;

  assert.equal(changed, false);
  assert.deepEqual(rendered, ["Alice current session"]);
});
