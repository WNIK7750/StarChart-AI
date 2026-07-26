import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

test("login dialog uses the site logo until a recent account avatar exists", () => {
  const source = read("frontend/assets/js/auth-ui.js");
  assert.match(source, /DEFAULT_AUTH_AVATAR = "assets\/img\/logo\.png"/);
  assert.match(source, /data-auth-avatar/);
  assert.match(source, /getRecentAvatarUrl\(\)/);
  assert.match(source, /rememberRecentAvatar\(avatarUrl\)/);
  assert.match(source, /input\[type=\"password\"\]/);
  assert.match(source, /name="phone" type="tel" autocomplete="tel"/);
  assert.match(source, /if \(mode === "login"\) body\.rememberMe/);
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
  assert.match(assistant, /window\.addEventListener\("ai-nav-auth-changed"/);
  assert.match(assistant, /renderGuestConversation/);
  assert.doesNotMatch(assistant, /importGuest|migrateGuest|syncGuest/);
  const authChangeHandler = assistant.match(
    /window\.addEventListener\("ai-nav-auth-changed", \(\) => \{([\s\S]*?)\n\}\);/,
  )?.[1] || "";
  assert.doesNotMatch(authChangeHandler, /clearGuestConversations|appendGuestMessage|recentGuestHistory/);
});
