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
  assert.deepEqual([...values.keys()].sort(), ["ai_nav_privacy_consent_2026-07-01", "ai_nav_recent_avatar_v1"]);
  assert.doesNotMatch(JSON.stringify([...values]), /password|token/i);
  delete globalThis.window;
});

test("login and settings dialogs expose the current detailed policy", () => {
  const auth = read("frontend/assets/js/auth-ui.js");
  const settings = read("frontend/settings.html");
  for (const source of [auth, settings]) {
    assert.match(source, /版本：2026-07-01/);
    assert.match(source, /不出售个人信息/);
    assert.match(source, /导出数据/);
    assert.match(source, /撤回/);
  }
});
