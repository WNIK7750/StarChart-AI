import {
  apiGet,
  clearAuthTokens,
  getAccessToken,
  restoreAuthSession,
  saveAuthTokens,
} from "./api.js";
import { withPublicBasePath } from "./public-path.js";
import { safeInternalHref } from "./url-safety.js";
import {
  confirmPasswordReset,
  getCurrentUser,
  getUserProfile,
  loginUser,
  logoutUser,
  registerUser,
  startPasswordReset,
} from "./users-api.js";
import {
  getRecentAvatarUrl,
  hasRememberedPrivacyConsent,
  rememberPrivacyConsent,
  rememberRecentAvatar,
} from "./auth-local-state.js";

const AUTH_STYLE_ID = "ai-nav-auth-style";
const AUTH_PANEL_ID = "authPanel";
const DEFAULT_AUTH_AVATAR = withPublicBasePath("/assets/img/brand-mark.62793ed5.svg");
let authEntryVisibility = {
  registration: false,
  recovery: false,
};
let authInitializationPromise = null;
let authEventsBound = false;
let authRefreshVersion = 0;
let latestAuthRefreshPromise = null;

export function publicAuthEntryVisibility(runtime) {
  return {
    registration: Boolean(runtime?.auth?.registration),
    recovery: Boolean(runtime?.auth?.recovery),
  };
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function injectStyles() {
  if (document.getElementById(AUTH_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = AUTH_STYLE_ID;
  style.textContent = `
    .auth-overlay{position:fixed;inset:0;z-index:120;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(10,10,15,.32);backdrop-filter:blur(12px)}
    .auth-overlay.open{display:flex}
    .auth-dialog{width:min(460px,100%);max-height:min(780px,calc(100vh - 32px));overflow:auto;border:1px solid rgba(255,255,255,.86);border-radius:24px;background:linear-gradient(145deg,#f8fbff,#ecf7ff);box-shadow:0 30px 80px rgba(25,52,92,.28)}
    .auth-head{display:flex;align-items:center;justify-content:space-between;padding:18px 20px 8px}.auth-head strong{font-size:19px;letter-spacing:-.02em}.auth-close{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.72);color:#425466;font-size:22px}
    .auth-avatar{width:68px;height:68px;margin:0 auto 12px;display:grid;place-items:center;overflow:hidden;border:3px solid #fff;border-radius:50%;background:#fff;box-shadow:0 10px 25px rgba(74,124,196,.24)}.auth-avatar img{width:100%;height:100%;object-fit:cover}
    .auth-tabs{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:0 20px;padding:5px;border-radius:14px;background:rgba(255,255,255,.6)}.auth-tabs button{height:38px;border-radius:10px;background:transparent;color:#6d7d8d;font-weight:750}.auth-tabs button.active{background:#fff;color:#1e2b39;box-shadow:0 3px 10px rgba(38,67,100,.1)}
    .auth-form{display:none;padding:16px 20px 22px}.auth-form.active{display:grid;gap:13px}.auth-field{display:grid;gap:6px}.auth-field label{font-size:13px;color:#526577;font-weight:700}.auth-field input{width:100%;min-height:46px;border:1px solid rgba(119,151,181,.22);border-radius:14px;padding:0 14px;font:inherit;background:rgba(255,255,255,.9);outline:none}.auth-field input:focus{border-color:#299eea;box-shadow:0 0 0 4px rgba(41,158,234,.13)}
    .auth-submit{height:46px;border-radius:14px;background:linear-gradient(135deg,#66bfff,#55aef1);color:#fff;font-size:16px;font-weight:800;box-shadow:0 10px 22px rgba(52,157,235,.26)}.auth-submit:hover{filter:brightness(.98)}.auth-ghost{height:38px;border-radius:10px;background:rgba(255,255,255,.7);color:#33475b;font-weight:700}.auth-error{min-height:18px;color:#c9435c;font-size:12px;line-height:1.5}.auth-note{color:#66798b;font-size:12px;line-height:1.7}.auth-line{display:flex;align-items:center;justify-content:space-between;gap:12px}.auth-link{color:#2388d2;font-weight:750}
    .auth-options{display:flex;justify-content:space-between;gap:12px;align-items:center;color:#6b7c8d;font-size:13px}.auth-check{display:inline-flex;align-items:center;gap:7px;cursor:pointer}.auth-check input{width:17px;height:17px;accent-color:#249cf0}.auth-consent{display:flex;align-items:flex-start;gap:8px;color:#657789;font-size:12px;line-height:1.6}.auth-consent input{width:17px;height:17px;flex:0 0 auto;margin-top:2px;accent-color:#249cf0}.auth-consent button{display:inline;color:#167fd0;font-weight:750;text-decoration:underline;text-underline-offset:2px}.auth-consent button:hover{color:#075f9f}
    .auth-legal{margin:0 20px 20px;padding:18px;border:0;border-radius:16px;background:#fff;color:#31485c;box-shadow:0 12px 35px rgba(37,66,96,.18)}.auth-legal::backdrop{background:rgba(9,23,42,.35);backdrop-filter:blur(4px)}.auth-legal h2{font-size:17px}.auth-legal p{margin-top:10px;font-size:13px;line-height:1.75;color:#5c7184}.auth-legal .auth-ghost{width:100%;margin-top:14px}
    .reset-questions{display:grid;gap:12px}
    .auth-form[hidden],.auth-tabs button[hidden],.auth-options button[hidden]{display:none!important}
    .user-menu{position:relative}.user-menu-btn{height:34px;display:inline-flex;align-items:center;gap:7px;padding:0 7px;border-radius:8px;background:transparent;color:#24292f;font-weight:700;white-space:nowrap;transition:background .16s,color .16s}.user-menu-btn:hover{background:rgba(31,35,40,.06)}.user-menu-btn.login-only{min-width:66px;justify-content:center;padding:0 12px;background:#24292f;color:#fff;font-weight:750;border-radius:8px}.user-menu-btn.login-only:hover{background:#32383f}.user-avatar{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(135deg,#7c5cff,#5ee0ff);font-size:12px;overflow:hidden;border:1px solid rgba(31,35,40,.10)}.user-avatar img{width:100%;height:100%;object-fit:cover}
    .user-popover{position:absolute;right:0;top:40px;width:276px;z-index:80;display:none;border:1px solid #d8dee4;border-radius:8px;background:#fff;box-shadow:0 12px 28px rgba(31,35,40,.12);overflow:hidden;font-size:13px;line-height:1.35}.user-menu.open .user-popover{display:block}
    .user-popover-head{display:flex;gap:10px;padding:10px 12px;border-bottom:1px solid #d8dee4}.user-popover-head .user-avatar{width:34px;height:34px}.user-popover-head strong{display:block;font-size:14px}.user-popover-head span{display:block;margin-top:2px;color:#57606a;font-size:12px}
    .user-popover-list{padding:6px}.user-popover-list a,.user-popover-list button{width:100%;height:31px;display:flex;align-items:center;gap:8px;padding:0 8px;border-radius:6px;color:#24292f;background:transparent;font-size:13px;font-weight:600;text-align:left}.user-popover-list a:hover,.user-popover-list button:hover{background:#f6f8fa}.user-popover-list .danger{color:#cf222e}.user-popover-sep{height:1px;background:#d8dee4;margin:6px}
  `;
  document.head.appendChild(style);
}

function authPanel() {
  let panel = document.getElementById(AUTH_PANEL_ID);
  if (panel) return panel;
  panel = document.createElement("div");
  panel.id = AUTH_PANEL_ID;
  panel.className = "auth-overlay";
  panel.innerHTML = `
    <div class="auth-dialog" role="dialog" aria-modal="true" aria-label="账号">
      <div class="auth-head"><strong>账号</strong><button class="auth-close" data-auth-close type="button" aria-label="关闭登录窗口">×</button></div>
      <div class="auth-avatar" aria-hidden="true"><img data-auth-avatar src="${DEFAULT_AUTH_AVATAR}" alt=""></div>
      <div class="auth-tabs" data-auth-tabs>
        <button class="active" data-auth-tab="login" type="button">登录</button>
        <button data-auth-tab="register" type="button">注册</button>
      </div>
      <form class="auth-form active" data-auth-form="login" novalidate>
        <div class="auth-field"><label>用户名 / 邮箱 / 手机</label><input name="identifier" autocomplete="username" required></div>
        <div class="auth-field"><label>密码</label><input name="password" type="password" autocomplete="current-password" required minlength="8"></div>
        <div class="auth-options"><label class="auth-check"><input name="rememberMe" type="checkbox"> 保持登录</label><button class="auth-link" data-auth-tab="reset-start" type="button">忘记密码？</button></div>
        <label class="auth-consent"><input name="privacyAccepted" type="checkbox" required><span>我已阅读并同意 <button data-auth-legal type="button">《服务协议与隐私政策》</button></span></label>
        <button class="auth-submit" type="submit">登录</button>
        <div class="auth-error" data-auth-error="login"></div>
      </form>
      <form class="auth-form" data-auth-form="register" novalidate>
        <div class="auth-field"><label>用户名</label><input name="username" autocomplete="username" required minlength="3" maxlength="32"></div>
        <div class="auth-field"><label>邮箱（可选）</label><input name="email" type="email" autocomplete="email"></div>
        <div class="auth-field"><label>手机号（可选）</label><input name="phone" type="tel" autocomplete="tel" maxlength="24" placeholder="中国大陆手机号或 + 国际区号"></div>
        <div class="auth-field"><label>展示名（可选）</label><input name="displayName" maxlength="40"></div>
        <div class="auth-field"><label>密码</label><input name="password" type="password" autocomplete="new-password" required minlength="8"></div>
        <label class="auth-consent"><input name="privacyAccepted" type="checkbox" required><span>我已阅读并同意 <button data-auth-legal type="button">《服务协议与隐私政策》</button></span></label>
        <button class="auth-submit" type="submit">创建账号</button>
        <div class="auth-error" data-auth-error="register"></div>
        <p class="auth-note">注册后会自动创建用户资料、偏好和普通用户角色；不会写入虚假学习数据。</p>
      </form>
      <form class="auth-form" data-auth-form="reset-start">
        <p class="auth-note">仅可通过账号已验证的外部恢复通道重置密码。无论账号是否存在，提交后都会显示相同结果。</p>
        <div class="auth-field"><label>用户名 / 邮箱 / 手机</label><input name="identifier" autocomplete="username" required></div>
        <button class="auth-submit" type="submit">发送恢复说明</button>
        <button class="auth-ghost" data-auth-tab="login" type="button">返回登录</button>
        <div class="auth-error" data-auth-error="reset-start"></div>
      </form>
      <form class="auth-form" data-auth-form="reset-confirm">
        <p class="auth-note">请填写从已验证恢复通道收到的一次性凭据。凭据将在使用或过期后失效。</p>
        <div class="auth-field"><label>一次性恢复凭据</label><input name="resetToken" autocomplete="one-time-code" required minlength="20" maxlength="160"></div>
        <div class="auth-field"><label>新密码</label><input name="newPassword" type="password" autocomplete="new-password" required minlength="8"></div>
        <button class="auth-submit" type="submit">重置密码</button>
        <button class="auth-ghost" data-auth-tab="reset-start" type="button">重新发送</button>
        <div class="auth-error" data-auth-error="reset-confirm"></div>
      </form>
      <dialog class="auth-legal" data-auth-legal-dialog aria-labelledby="authLegalTitle">
        <h2 id="authLegalTitle">服务协议与隐私政策</h2>
        <p><strong>版本：2026-07-20。</strong>使用账号服务时，请遵守法律法规，不得利用本站干扰服务、侵害他人权益或提交违法内容。本站可为安全、维护或合规需要限制异常账号与会话。</p>
        <p>为提供账号、学习记录与个性化功能，本站会处理账号资料、头像、登录设备与会话信息，以及你主动产生的学习进度、收藏和工作流数据；这些信息仅用于身份验证、功能交付、安全审计与故障排查，不出售个人信息。</p>
        <p>启用 AI 模型服务时，本站会将当前问题和站内公开证据发送至位于中国内地北京区域的阿里云百炼千问处理，用于生成本次回答；不会发送账号资料、用户资产或长期记忆。生产启用以完成数据处理协议、明确数据不用于模型训练并落实约定留存策略为前提。请勿在问题中提交密码、令牌、联系方式或其他敏感个人信息。</p>
        <p>密码以不可逆安全散列保存，刷新令牌通过 HttpOnly Cookie 管理。数据按业务与安全需要保留；你可在“设置 · 隐私与数据”查询同意状态、导出数据、申请注销或撤回同意。撤回后需在登录时重新同意当前版本。</p>
        <button class="auth-ghost" data-auth-legal-close type="button">我已了解</button>
      </dialog>
    </div>`;
  document.body.appendChild(panel);
  return panel;
}

function openAuth(mode = "login") {
  renderAuthDialogAvatar();
  authPanel().classList.add("open");
  setAuthTab(mode);
  restoreConsentChoice();
}

function restoreConsentChoice() {
  const accepted = hasRememberedPrivacyConsent();
  authPanel().querySelectorAll('[name="privacyAccepted"]').forEach((input) => { input.checked = accepted; });
}

function safeAvatarUrl(value) {
  if (!value) return DEFAULT_AUTH_AVATAR;
  try {
    return withPublicBasePath(value);
  } catch {
    return DEFAULT_AUTH_AVATAR;
  }
}

function renderAuthDialogAvatar() {
  const image = authPanel().querySelector("[data-auth-avatar]");
  image.src = safeAvatarUrl(getRecentAvatarUrl());
}

function setAuthTab(mode) {
  if (mode === "register" && !authEntryVisibility.registration) mode = "login";
  if (mode.startsWith("reset") && !authEntryVisibility.recovery) mode = "login";
  const panel = authPanel();
  const authTabs = panel.querySelector("[data-auth-tabs]");
  authTabs.style.display = mode.startsWith("reset") ? "none" : "grid";
  panel.querySelectorAll("[data-auth-tab]").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.authTab === mode);
  });
  panel.querySelectorAll("[data-auth-form]").forEach((form) => {
    form.classList.toggle("active", form.dataset.authForm === mode);
  });
}

export function applyPublicAuthCapabilities(runtime, panel = authPanel()) {
  authEntryVisibility = publicAuthEntryVisibility(runtime);
  panel.querySelector('[data-auth-tab="register"]').hidden = !authEntryVisibility.registration;
  panel.querySelectorAll('[data-auth-tab^="reset"]').forEach((entry) => {
    entry.hidden = !authEntryVisibility.recovery;
  });
  panel.querySelector('[data-auth-form="register"]').hidden = !authEntryVisibility.registration;
  panel.querySelectorAll('[data-auth-form^="reset"]').forEach((form) => {
    form.hidden = !authEntryVisibility.recovery;
  });
  const activeForm = panel.querySelector("[data-auth-form].active");
  if (
    (activeForm?.dataset.authForm === "register" && !authEntryVisibility.registration)
    || (activeForm?.dataset.authForm?.startsWith("reset") && !authEntryVisibility.recovery)
  ) {
    setAuthTab("login");
  }
}

async function loadPublicAuthCapabilities() {
  try {
    applyPublicAuthCapabilities(await apiGet("/runtime/public"));
  } catch {
    applyPublicAuthCapabilities(null);
  }
}

function userInitial(user) {
  return (user?.username || user?.email || "U").slice(0, 1).toUpperCase();
}

function avatarMarkup(user, avatarUrl = "") {
  return avatarUrl
    ? `<img src="${escapeHtml(safeAvatarUrl(avatarUrl))}" alt="">`
    : escapeHtml(userInitial(user));
}

function findActionContainers() {
  return Array.from(document.querySelectorAll(".nav-actions, .top-actions"));
}

function renderLoggedOut() {
  findActionContainers().forEach((container) => {
    const existing = container.querySelector("[data-auth-root]");
    if (existing) existing.remove();
    const root = document.createElement("div");
    root.className = "user-menu";
    root.dataset.authRoot = "1";
    root.innerHTML = '<button class="user-menu-btn login-only" type="button" data-auth-trigger="login">登录</button>';
    container.appendChild(root);
  });
}

function renderLoggedIn(user, avatarUrl = "", profile = {}) {
  rememberRecentAvatar(avatarUrl);
  renderAuthDialogAvatar();
  findActionContainers().forEach((container) => {
    container.querySelectorAll("[data-auth-trigger]").forEach((item) => item.remove());
    const existing = container.querySelector("[data-auth-root]");
    if (existing) existing.remove();
    const root = document.createElement("div");
    root.className = "user-menu";
    root.dataset.authRoot = "1";
    const displayName = profile.displayName || user.username || "我的账号";
    root.innerHTML = `
      <button class="user-menu-btn" type="button" data-user-menu>
        <span class="user-avatar">${avatarMarkup(user, avatarUrl)}</span>
        <span>${escapeHtml(user.username || "我的账号")}</span>
      </button>
      <div class="user-popover">
        <div class="user-popover-head">
          <span class="user-avatar">${avatarMarkup(user, avatarUrl)}</span>
          <div><strong>${escapeHtml(displayName)}</strong><span>@${escapeHtml(user.username || "user")}</span></div>
        </div>
        <div class="user-popover-list">
          <a href="${escapeHtml(safeInternalHref("/settings#profile"))}">个人资料</a>
          <a href="${escapeHtml(safeInternalHref("/settings#account"))}">账号设置</a>
          <a href="${escapeHtml(safeInternalHref("/settings#security"))}">密码与密保</a>
          <a href="${escapeHtml(safeInternalHref("/settings#sessions"))}">登录设备</a>
          <div class="user-popover-sep"></div>
          <a href="${escapeHtml(safeInternalHref("/settings#learning"))}">学习空间</a>
          <a href="${escapeHtml(safeInternalHref("/settings#workflows"))}">工作流</a>
          <div class="user-popover-sep"></div>
          <button class="danger" type="button" data-logout>退出登录</button>
        </div>
      </div>`;
    container.appendChild(root);
  });
}

function refreshAuthUI() {
  const refreshVersion = ++authRefreshVersion;
  const refreshPromise = (async () => {
    if (!getAccessToken()) {
      try {
        await restoreAuthSession();
      } catch {
        if (refreshVersion !== authRefreshVersion) return latestAuthRefreshPromise;
        renderLoggedOut();
        return null;
      }
    }
    try {
      const [{ user }, profileResult] = await Promise.all([
        getCurrentUser(),
        getUserProfile().catch(() => ({ profile: {} })),
      ]);
      if (refreshVersion !== authRefreshVersion) return latestAuthRefreshPromise;
      renderLoggedIn(user, profileResult.profile?.avatarUrl || "", profileResult.profile || {});
      return user;
    } catch {
      if (refreshVersion !== authRefreshVersion) return latestAuthRefreshPromise;
      clearAuthTokens();
      renderLoggedOut();
      return null;
    }
  })();
  latestAuthRefreshPromise = refreshPromise;
  return refreshPromise;
}

async function handleLoginOrRegister(form, mode) {
  const body = Object.fromEntries(new FormData(form).entries());
  body.privacyAccepted = body.privacyAccepted === "on";
  if (mode === "login") body.rememberMe = body.rememberMe === "on";
  if (!body.privacyAccepted) throw new Error("请先阅读并同意服务协议与隐私政策");
  const data = mode === "register"
    ? await registerUser(body)
    : await loginUser({ ...body, deviceName: "浏览器" });
  rememberPrivacyConsent(true);
  saveAuthTokens(data);
  const authenticatedRefresh = refreshAuthUI();
  form.querySelectorAll('input[type="password"]').forEach((input) => { input.value = ""; });
  authPanel().classList.remove("open");
  await import("./anonymous-learning-state.js")
    .then(({ mergeAnonymousLearningState }) => mergeAnonymousLearningState())
    .catch((error) => console.warn("Anonymous learning state import unavailable:", error));
  return authenticatedRefresh;
}

async function handleResetStart(form) {
  const body = Object.fromEntries(new FormData(form).entries());
  const data = await startPasswordReset(body);
  setAuthTab("reset-confirm");
  authPanel().querySelector('[data-auth-error="reset-confirm"]').textContent = data.message;
}

async function handleResetConfirm(form) {
  const body = Object.fromEntries(new FormData(form).entries());
  await confirmPasswordReset(body);
  form.reset();
  setAuthTab("login");
  authPanel().querySelector('[data-auth-error="login"]').textContent = "密码已重置，请使用新密码登录。";
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const mode = form.dataset.authForm;
  const error = document.querySelector(`[data-auth-error="${mode}"]`);
  error.textContent = "";
  try {
    if (mode === "login" || mode === "register") await handleLoginOrRegister(form, mode);
    if (mode === "reset-start") await handleResetStart(form);
    if (mode === "reset-confirm") await handleResetConfirm(form);
  } catch (err) {
    error.textContent = err.message || "操作失败";
  }
}

async function logout() {
  try {
    await logoutUser();
  } catch {
    // Local logout should still succeed when the server-side session is already invalid.
  }
  clearAuthTokens();
  document.querySelectorAll(".user-menu.open").forEach((item) => item.classList.remove("open"));
  renderLoggedOut();
}

function bindAuthEvents() {
  if (authEventsBound) return;
  authEventsBound = true;
  document.addEventListener("click", async (event) => {
    const target = event.target;
    const trigger = target.closest("[data-auth-trigger]");
    if (trigger) openAuth(trigger.dataset.authTrigger || "login");
    if (target.closest("[data-auth-close]")) authPanel().classList.remove("open");
    if (target.closest("[data-auth-legal]")) authPanel().querySelector("[data-auth-legal-dialog]").showModal();
    if (target.closest("[data-auth-legal-close]")) authPanel().querySelector("[data-auth-legal-dialog]").close();
    const tab = target.closest("[data-auth-tab]");
    if (tab) setAuthTab(tab.dataset.authTab);
    const menuButton = target.closest("[data-user-menu]");
    if (menuButton) menuButton.closest(".user-menu").classList.toggle("open");
    if (target.closest("[data-logout]")) await logout();
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".user-menu")) {
      document.querySelectorAll(".user-menu.open").forEach((item) => item.classList.remove("open"));
    }
  });
  document.querySelectorAll("[data-auth-form]").forEach((form) => form.addEventListener("submit", handleAuthSubmit));
  authPanel().querySelectorAll('[name="privacyAccepted"]').forEach((input) => {
    input.addEventListener("change", () => {
      const form = input.closest("[data-auth-form]");
      if (input.checked && form) form.querySelector("[data-auth-error]").textContent = "";
    });
  });
}

export function initAuthUI() {
  if (authInitializationPromise) return authInitializationPromise;
  injectStyles();
  const panel = authPanel();
  applyPublicAuthCapabilities(null, panel);
  renderLoggedOut();
  bindAuthEvents();
  authInitializationPromise = Promise.all([
    loadPublicAuthCapabilities(),
    refreshAuthUI(),
  ]).then(([, user]) => user);
  return authInitializationPromise;
}
