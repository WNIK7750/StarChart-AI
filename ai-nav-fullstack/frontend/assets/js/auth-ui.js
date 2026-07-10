import {
  apiGet,
  apiPost,
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  saveAuthTokens,
} from "./api.js";

const AUTH_STYLE_ID = "ai-nav-auth-style";
const AUTH_PANEL_ID = "authPanel";

let resetState = {
  uid: "",
  token: "",
};

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
    .auth-dialog{width:min(420px,100%);max-height:min(720px,calc(100vh - 48px));overflow:auto;border:1px solid #d8dee4;border-radius:10px;background:#fff;box-shadow:0 16px 40px rgba(31,35,40,.16)}
    .auth-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #d8dee4}
    .auth-head strong{font-size:18px}.auth-close{width:30px;height:30px;border-radius:7px;background:#f6f8fa}
    .auth-tabs{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:14px 16px 0}.auth-tabs button{height:36px;border-radius:8px;background:#f6f8fa;color:#57606a;font-weight:750}.auth-tabs button.active{background:#24292f;color:#fff}
    .auth-form{display:none;padding:14px 16px 18px}.auth-form.active{display:grid;gap:12px}
    .auth-field{display:grid;gap:6px}.auth-field label{font-size:13px;color:#57606a;font-weight:650}.auth-field input{width:100%;min-height:38px;border:1px solid #d0d7de;border-radius:8px;padding:0 10px;font:inherit;background:#fff;outline:none}.auth-field input:focus{border-color:#0969da;box-shadow:0 0 0 3px rgba(9,105,218,.12)}
    .auth-submit{height:40px;border-radius:8px;background:#24292f;color:#fff;font-weight:750}.auth-ghost{height:36px;border-radius:8px;background:#f6f8fa;color:#24292f;font-weight:700}.auth-error{min-height:18px;color:#cf222e;font-size:12px;line-height:1.5}.auth-note{color:#57606a;font-size:12px;line-height:1.7}.auth-line{display:flex;align-items:center;justify-content:space-between;gap:12px}.auth-link{color:#0969da;font-weight:700}
    .reset-questions{display:grid;gap:12px}
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
      <div class="auth-head"><strong>账号</strong><button class="auth-close" data-auth-close type="button">×</button></div>
      <div class="auth-tabs" data-auth-tabs>
        <button class="active" data-auth-tab="login" type="button">登录</button>
        <button data-auth-tab="register" type="button">注册</button>
      </div>
      <form class="auth-form active" data-auth-form="login">
        <div class="auth-field"><label>用户名 / 邮箱 / 手机</label><input name="identifier" autocomplete="username" required></div>
        <div class="auth-field"><label>密码</label><input name="password" type="password" autocomplete="current-password" required minlength="8"></div>
        <div class="auth-line"><button class="auth-link" data-auth-tab="reset-start" type="button">忘记密码？</button></div>
        <button class="auth-submit" type="submit">登录</button>
        <div class="auth-error" data-auth-error="login"></div>
      </form>
      <form class="auth-form" data-auth-form="register">
        <div class="auth-field"><label>用户名</label><input name="username" autocomplete="username" required minlength="3" maxlength="32"></div>
        <div class="auth-field"><label>邮箱（可选）</label><input name="email" type="email" autocomplete="email"></div>
        <div class="auth-field"><label>展示名（可选）</label><input name="displayName" maxlength="40"></div>
        <div class="auth-field"><label>密码</label><input name="password" type="password" autocomplete="new-password" required minlength="8"></div>
        <button class="auth-submit" type="submit">创建账号</button>
        <div class="auth-error" data-auth-error="register"></div>
        <p class="auth-note">注册后会自动创建用户资料、偏好和普通用户角色；不会写入虚假学习数据。</p>
      </form>
      <form class="auth-form" data-auth-form="reset-start">
        <p class="auth-note">通过已设置的密保问题找回密码。密保问题需要先在用户设置中开启。</p>
        <div class="auth-field"><label>用户名 / 邮箱 / 手机</label><input name="identifier" autocomplete="username" required></div>
        <button class="auth-submit" type="submit">验证身份</button>
        <button class="auth-ghost" data-auth-tab="login" type="button">返回登录</button>
        <div class="auth-error" data-auth-error="reset-start"></div>
      </form>
      <form class="auth-form" data-auth-form="reset-verify">
        <div class="reset-questions" data-reset-questions></div>
        <button class="auth-submit" type="submit">提交答案</button>
        <button class="auth-ghost" data-auth-tab="reset-start" type="button">重新填写账号</button>
        <div class="auth-error" data-auth-error="reset-verify"></div>
      </form>
      <form class="auth-form" data-auth-form="reset-confirm">
        <div class="auth-field"><label>新密码</label><input name="newPassword" type="password" autocomplete="new-password" required minlength="8"></div>
        <button class="auth-submit" type="submit">重置密码</button>
        <div class="auth-error" data-auth-error="reset-confirm"></div>
      </form>
    </div>`;
  document.body.appendChild(panel);
  return panel;
}

function openAuth(mode = "login") {
  authPanel().classList.add("open");
  setAuthTab(mode);
}

function setAuthTab(mode) {
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

function userInitial(user) {
  return (user?.username || user?.email || "U").slice(0, 1).toUpperCase();
}

function avatarMarkup(user, avatarUrl = "") {
  return avatarUrl ? `<img src="${escapeHtml(avatarUrl)}" alt="">` : escapeHtml(userInitial(user));
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
    root.innerHTML = '<button class="user-menu-btn login-only" type="button" data-auth-trigger="login">登入</button>';
    container.appendChild(root);
  });
}

function renderLoggedIn(user, avatarUrl = "", profile = {}) {
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
          <a href="settings.html#profile">个人资料</a>
          <a href="settings.html#account">账号设置</a>
          <a href="settings.html#security">密码与密保</a>
          <a href="settings.html#sessions">登录设备</a>
          <div class="user-popover-sep"></div>
          <a href="settings.html#learning">学习空间</a>
          <a href="settings.html#workflows">工作流</a>
          <div class="user-popover-sep"></div>
          <button class="danger" type="button" data-logout>退出登录</button>
        </div>
      </div>`;
    container.appendChild(root);
  });
}

async function refreshAuthUI() {
  if (!getAccessToken()) {
    renderLoggedOut();
    return;
  }
  try {
    const [{ user }, profileResult] = await Promise.all([
      apiGet("/auth/me"),
      apiGet("/users/me/profile").catch(() => ({ profile: {} })),
    ]);
    renderLoggedIn(user, profileResult.profile?.avatarUrl || "", profileResult.profile || {});
  } catch {
    clearAuthTokens();
    renderLoggedOut();
  }
}

async function handleLoginOrRegister(form, mode) {
  const body = Object.fromEntries(new FormData(form).entries());
  const data = mode === "register"
    ? await apiPost("/auth/register", body)
    : await apiPost("/auth/login", { ...body, deviceName: "浏览器" });
  saveAuthTokens(data);
  authPanel().classList.remove("open");
  await refreshAuthUI();
}

async function handleResetStart(form) {
  const body = Object.fromEntries(new FormData(form).entries());
  const data = await apiPost("/auth/password-reset/security/start", body);
  resetState = { uid: data.resetUid, token: "" };
  const box = authPanel().querySelector("[data-reset-questions]");
  box.innerHTML = (data.questions || []).map((item, index) => `
    <div class="auth-field">
      <label>${escapeHtml(item.question)}</label>
      <input name="answer${index}" data-answer autocomplete="off" required minlength="2" maxlength="80">
    </div>`).join("");
  setAuthTab("reset-verify");
}

async function handleResetVerify(form) {
  const answers = Array.from(form.querySelectorAll("[data-answer]")).map((input) => input.value);
  const data = await apiPost("/auth/password-reset/security/verify", {
    resetUid: resetState.uid,
    answers,
  });
  resetState.token = data.resetToken;
  setAuthTab("reset-confirm");
}

async function handleResetConfirm(form) {
  const body = Object.fromEntries(new FormData(form).entries());
  await apiPost("/auth/password-reset/security/confirm", {
    resetToken: resetState.token,
    newPassword: body.newPassword,
  });
  resetState = { uid: "", token: "" };
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
    if (mode === "reset-verify") await handleResetVerify(form);
    if (mode === "reset-confirm") await handleResetConfirm(form);
  } catch (err) {
    error.textContent = err.message || "操作失败";
  }
}

async function logout() {
  try {
    const refreshToken = getRefreshToken();
    if (refreshToken) await apiPost("/auth/logout", { refreshToken });
  } catch {
    // Local logout should still succeed when the server-side session is already invalid.
  }
  clearAuthTokens();
  document.querySelectorAll(".user-menu.open").forEach((item) => item.classList.remove("open"));
  renderLoggedOut();
}

export async function initAuthUI() {
  injectStyles();
  authPanel();
  document.addEventListener("click", async (event) => {
    const target = event.target;
    const trigger = target.closest("[data-auth-trigger]");
    if (trigger) openAuth(trigger.dataset.authTrigger || "login");
    if (target.closest("[data-auth-close]")) authPanel().classList.remove("open");
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
  await refreshAuthUI();
}
