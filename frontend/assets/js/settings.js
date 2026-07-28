import {
  apiGet,
  clearAuthTokens,
} from "./api.js";
import { initAuthUI } from "./auth-ui.js";
import { withPublicBasePath } from "./public-path.js";
import { rememberPrivacyConsent, rememberRecentAvatar } from "./auth-local-state.js";
import { formatLearningTime, learningTimeTitle } from "./time-format.js";
import { safeInternalHref } from "./url-safety.js";
import {
  getLearningDashboard,
  listLearningFavorites,
  listLearningProgress,
  listRecentLearning,
  removeLearningFavorite,
} from "./learning-api.js";
import {
  archiveUserWorkflow,
  cancelUserDeletion,
  exportUserData,
  getCurrentUser,
  getCurrentDeletionRequest,
  getUserAccount,
  getUserPreferences,
  getUserPrivacyConsents,
  getUserProfile,
  getUserSecurityQuestions,
  listUserSessions,
  listUserWorkflows,
  logoutUser,
  revokeOtherUserSessions,
  revokeUserSession,
  requestUserDeletion,
  updateUserAccount,
  updateUserPassword,
  updateUserPreferences,
  updateUserPrivacyConsent,
  updateUserProfile,
  updateUserSecurityQuestions,
  uploadUserAvatar,
} from "./users-api.js";

const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
const MAX_AVATAR_SOURCE_PIXELS = 20_000_000;
const ALLOWED_AVATAR_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
let cropState = null;
let cropReturnFocus = null;
let profileVersion = null;
let preferencesVersion = null;
let agentMemoryPolicyVersion = null;
let agentMemoryConsentGranted = false;
let privacyPolicyVersion = null;
let currentUser = null;
let accountSnapshot = null;
const CROP_RADIUS_RATIO = 0.39;
let settingsVisibility = {
  identityChanges: false,
  passwordChanges: false,
  recovery: false,
  privacyWrites: false,
};

export function publicSettingsVisibility(runtime) {
  const identityChanges = Boolean(runtime?.auth?.identityChanges);
  return {
    identityChanges,
    passwordChanges: identityChanges,
    recovery: Boolean(runtime?.auth?.recovery),
    privacyWrites: Boolean(runtime?.auth?.privacyWrites),
  };
}

export function projectAvatarUrl(url = "") {
  if (!url) return "";
  try {
    return withPublicBasePath(url);
  } catch {
    return "";
  }
}

const FORM_REGIONS = {
  profile: ["[data-profile-form]", "[data-profile-message]"],
  account: ["[data-account-form]", "[data-account-message]"],
  password: ["[data-password-form]", "[data-password-message]"],
  security: ["[data-security-form]", "[data-security-message]"],
  preferences: ["[data-preferences-form]", "[data-preferences-message]"],
};

function $(selector, root = document) {
  return root.querySelector(selector);
}

function $all(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setMessage(selector, message, isError = false) {
  const node = $(selector);
  if (!node) return;
  node.textContent = message;
  node.classList.toggle("error", isError);
  node.setAttribute("role", isError ? "alert" : "status");
  node.setAttribute("aria-live", "polite");
}

function setFormState(region, state, message = "", retry = false) {
  const [formSelector, messageSelector] = FORM_REGIONS[region];
  const form = $(formSelector);
  const messageNode = $(messageSelector);
  const busy = state === "loading" || state === "saving";
  form.dataset.state = state;
  form.setAttribute("aria-busy", String(busy));
  form.querySelectorAll("input, textarea, select, button").forEach((control) => {
    control.disabled = busy;
  });
  const submit = form.querySelector("button[type='submit']");
  if (submit) {
    submit.dataset.idleLabel ||= submit.textContent;
    submit.textContent = state === "saving" ? "保存中..." : submit.dataset.idleLabel;
  }
  messageNode.textContent = message;
  messageNode.classList.toggle("error", state === "error");
  messageNode.setAttribute("role", state === "error" ? "alert" : "status");
  messageNode.setAttribute("aria-live", "polite");
  if (retry) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "retry-btn";
    button.dataset.retryArea = region;
    button.textContent = "重试";
    messageNode.appendChild(button);
  }
}

function stateBlock(message, retryArea = "", loading = false) {
  const retry = retryArea
    ? `<button class="retry-btn" type="button" data-retry-area="${escapeHtml(retryArea)}">重试</button>`
    : "";
  const dot = loading ? '<span class="state-dot" aria-hidden="true"></span>' : "";
  return `<div class="reserved state-block${loading ? " loading" : ""}" role="${retryArea ? "alert" : "status"}">${dot}<span>${escapeHtml(message)}</span>${retry}</div>`;
}

function setContentLoading(selector, message = "正在读取...") {
  const box = $(selector);
  box.setAttribute("aria-busy", "true");
  box.innerHTML = stateBlock(message, "", true);
}

function setSectionVisible(name, visible, root = document) {
  const section = $(`[data-section="${name}"]`, root);
  const link = $(`[data-section-link][href="#${name}"]`, root);
  if (section) section.hidden = !visible;
  if (link) link.hidden = !visible;
}

export function applyPublicSettingsCapabilities(runtime, root = document) {
  settingsVisibility = publicSettingsVisibility(runtime);
  setSectionVisible("account", settingsVisibility.identityChanges, root);

  const passwordPanel = $("[data-password-form]", root)?.closest(".panel");
  const recoveryPanel = $("[data-security-form]", root)?.closest(".panel");
  if (passwordPanel) passwordPanel.hidden = !settingsVisibility.passwordChanges;
  if (recoveryPanel) recoveryPanel.hidden = !settingsVisibility.recovery;
  setSectionVisible(
    "security",
    settingsVisibility.passwordChanges || settingsVisibility.recovery,
    root,
  );

  const privacyInput = $("[data-privacy-consent-form] [name='privacyPolicy']", root);
  if (privacyInput) {
    privacyInput.disabled = !settingsVisibility.privacyWrites;
    const privacyWriteControl = privacyInput.closest("label");
    if (privacyWriteControl) privacyWriteControl.hidden = !settingsVisibility.privacyWrites;
  }
  const agentMemoryInput = $("[data-preferences-form] [name='agentMemoryEnabled']", root);
  if (agentMemoryInput) {
    agentMemoryInput.disabled = !settingsVisibility.privacyWrites;
    const agentMemoryControl = agentMemoryInput.closest("label");
    if (agentMemoryControl) agentMemoryControl.hidden = !settingsVisibility.privacyWrites;
  }
  const deletionForm = $("[data-deletion-form]", root);
  if (deletionForm) {
    deletionForm.hidden = !settingsVisibility.privacyWrites;
    deletionForm.disabled = !settingsVisibility.privacyWrites;
    deletionForm.querySelectorAll?.("input, select, textarea, button").forEach((control) => {
      control.disabled = !settingsVisibility.privacyWrites;
    });
  }
  $all("[data-cancel-deletion]", root).forEach((control) => {
    control.hidden = !settingsVisibility.privacyWrites;
    control.disabled = !settingsVisibility.privacyWrites;
  });
}

async function loadPublicSettingsCapabilities() {
  try {
    applyPublicSettingsCapabilities(await apiGet("/runtime/public"));
  } catch {
    applyPublicSettingsCapabilities(null);
  }
}

function showSection(name = "profile") {
  const requested = $(`[data-section="${name || "profile"}"]`);
  const sectionName = requested && !requested.hidden ? requested.dataset.section : "profile";
  $all("[data-section]").forEach((section) => {
    section.classList.toggle("active", section.dataset.section === sectionName);
  });
  $all("[data-section-link]").forEach((link) => {
    const active = link.getAttribute("href") === `#${sectionName}`;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

function wireFormLabels(root = document) {
  $all(".field > label", root).forEach((label, index) => {
    const control = label.parentElement?.querySelector("input, textarea, select");
    if (!control) return;
    control.id ||= `settings-field-${control.name || "control"}-${index}`;
    label.htmlFor = control.id;
  });
}

function confirmAction({ title, message, confirmLabel = "确认" }) {
  const dialog = $("[data-confirm-dialog]");
  const opener = document.activeElement;
  $("[data-confirm-title]", dialog).textContent = title;
  $("[data-confirm-message]", dialog).textContent = message;
  const accept = $("[data-confirm-accept]", dialog);
  const cancel = $("[data-confirm-cancel]", dialog);
  accept.textContent = confirmLabel;

  return new Promise((resolve) => {
    let settled = false;
    const finish = (accepted) => {
      if (settled) return;
      settled = true;
      accept.removeEventListener("click", onAccept);
      cancel.removeEventListener("click", onCancel);
      dialog.removeEventListener("cancel", onDialogCancel);
      if (dialog.open) dialog.close();
      window.setTimeout(() => opener?.focus?.(), 0);
      resolve(accepted);
    };
    const onAccept = () => finish(true);
    const onCancel = () => finish(false);
    const onDialogCancel = (event) => {
      event.preventDefault();
      finish(false);
    };
    accept.addEventListener("click", onAccept);
    cancel.addEventListener("click", onCancel);
    dialog.addEventListener("cancel", onDialogCancel);
    dialog.showModal();
    accept.focus();
  });
}

function renderAvatar(url, remember = false) {
  const src = projectAvatarUrl(url);
  if (remember) rememberRecentAvatar(url);
  $all("[data-avatar-preview], [data-avatar-small]").forEach((image) => {
    image.src = src || "assets/img/logo.png";
  });
}

function fillQuestionRows(items = []) {
  const defaults = [
    "你的第一位启蒙老师是谁？",
    "你最熟悉的一门课程是什么？",
    "你最常用的学习工具是什么？",
  ];
  const box = $("[data-question-list]");
  box.innerHTML = defaults.map((fallback, index) => {
    const item = items[index] || {};
    return `
      <div class="question-row">
        <div class="field"><label>问题 ${index + 1}</label><input name="question${index}" value="${escapeHtml(item.question || fallback)}" required minlength="2" maxlength="80"></div>
        <div class="field"><label>答案 ${index + 1}</label><input name="answer${index}" autocomplete="off" required minlength="2" maxlength="80" placeholder="保存后不会明文展示"></div>
      </div>`;
  }).join("");
  wireFormLabels(box);
}

function requireLogin(user) {
  return user || null;
}

function renderLoginRequired() {
  $("[data-settings-content]").hidden = true;
  const gate = $("[data-settings-login-required]");
  gate.hidden = false;
  gate.querySelector('[data-auth-trigger="login"]')?.focus();
}

async function loadAccountDetails(user = currentUser) {
  setFormState("account", "loading", "正在读取账号...");
  try {
    const data = await getUserAccount();
    accountSnapshot = data.account;
    const username = data.account.username || user?.username || "";
    const form = $("[data-account-form]");
    form.username.value = username;
    form.email.value = data.account.email || "";
    form.phone.value = data.account.phone || "";
    form.currentPassword.value = "";
    $("[data-account-email-status]").textContent = data.account.email
      ? `当前状态：${data.account.emailVerified ? "已验证" : "未验证"}`
      : "尚未绑定邮箱";
    $("[data-account-phone-status]").textContent = data.account.phone
      ? `当前状态：${data.account.phoneVerified ? "已验证" : "未验证"}`
      : "尚未绑定手机号";
    $("[data-user-name]").textContent = `@${username || "user"}`;
    setFormState("account", "idle");
  } catch (error) {
    setFormState("account", "error", error.message || "账号加载失败。", true);
  }
}

async function loadProfile(user = currentUser) {
  setFormState("profile", "loading", "正在读取资料...");
  try {
    const { profile } = await getUserProfile();
    profileVersion = profile.version;
    const form = $("[data-profile-form]");
    form.displayName.value = profile.displayName || "";
    form.learningLevel.value = profile.learningLevel || "beginner";
    form.targetDirection.value = profile.targetDirection || "";
    form.bio.value = profile.bio || "";
    $("[data-user-display]").textContent = profile.displayName || user?.username || "用户设置";
    renderAvatar(profile.avatarUrl, true);
    setFormState("profile", "idle");
  } catch (error) {
    renderAvatar("");
    setFormState("profile", "error", error.message || "资料加载失败。", true);
  }
}

async function loadPreferences() {
  setFormState("preferences", "loading", "正在读取偏好...");
  try {
    const [{ preferences }, consentData] = await Promise.all([
      getUserPreferences(),
      getUserPrivacyConsents(),
    ]);
    preferencesVersion = preferences.version;
    const form = $("[data-preferences-form]");
    form.cnFirst.checked = Boolean(preferences.cnFirst);
    form.freeFirst.checked = Boolean(preferences.freeFirst);
    form.showExternalResources.checked = Boolean(preferences.showExternalResources);
    const agentConsent = consentData.items.find((item) => item.consentType === "agent_memory");
    agentMemoryPolicyVersion = agentConsent?.policyVersion || null;
    agentMemoryConsentGranted = agentConsent?.status === "granted";
    form.agentMemoryEnabled.checked = agentMemoryConsentGranted;
    setFormState("preferences", "idle");
  } catch (error) {
    setFormState("preferences", "error", error.message || "偏好加载失败。", true);
  }
}

async function loadSecurityQuestions() {
  setFormState("security", "loading", "正在读取密保状态...");
  try {
    const data = await getUserSecurityQuestions();
    $("[data-security-status]").textContent = data.configured
      ? `已设置 ${data.items.length} 个密保问题。修改时需要重新填写答案。`
      : "尚未设置密保问题。设置后可在登录页找回密码。";
    fillQuestionRows(data.items);
    setFormState("security", "idle");
  } catch (error) {
    $("[data-security-status]").textContent = "密保状态暂不可用。";
    fillQuestionRows();
    setFormState("security", "error", error.message || "密保状态加载失败。", true);
  }
}

async function loadAccount(user) {
  const loaders = [
    loadProfile(user),
    loadPreferences(),
  ];
  if (settingsVisibility.identityChanges) loaders.push(loadAccountDetails(user));
  if (settingsVisibility.recovery) loaders.push(loadSecurityQuestions());
  await Promise.all(loaders);
}

async function loadAtomicAreas() {
  await Promise.all([loadSessions(), loadLearningAreas(), loadPrivacy(), loadWorkflows()]);
}

function renderDeletionStatus(request) {
  const box = $("[data-deletion-status]");
  const form = $("[data-deletion-form]");
  if (!box || !form) return;
  if (!request) {
    box.textContent = "当前没有进行中的账号注销申请。";
    form.hidden = !settingsVisibility.privacyWrites;
    return;
  }
  box.innerHTML = `<div><strong>注销申请待执行</strong><p class="hint">计划执行时间：${escapeHtml(request.scheduledFor || "待定")}</p></div>
    ${request.status === "pending" && settingsVisibility.privacyWrites ? `<button class="btn subtle" type="button" data-cancel-deletion="${escapeHtml(request.requestUid)}">取消申请</button>` : ""}`;
  form.hidden = true;
}

async function loadPrivacy() {
  setMessage("[data-privacy-consent-message]", "正在读取隐私同意...");
  try {
    const consents = await getUserPrivacyConsents();
    const policy = consents.items.find((item) => item.consentType === "privacy_policy");
    privacyPolicyVersion = policy?.policyVersion || null;
    $("[data-privacy-consent-form] [name='privacyPolicy']").checked = policy?.status === "granted";
    rememberPrivacyConsent(policy?.status === "granted");
    $("[data-privacy-policy-version]").textContent = privacyPolicyVersion
      ? `当前政策版本：${privacyPolicyVersion}`
      : "隐私政策版本暂不可用。";
    setMessage("[data-privacy-consent-message]", policy?.status === "granted" ? "当前状态：已同意" : "当前状态：未同意，无法登录。", policy?.status !== "granted");
  } catch (error) {
    setMessage("[data-privacy-consent-message]", error.message || "隐私设置加载失败。", true);
  }
}

async function savePrivacyConsent(event) {
  event.preventDefault();
  const form = event.currentTarget.form || event.currentTarget;
  if (!privacyPolicyVersion) {
    setMessage("[data-privacy-consent-message]", "隐私政策版本不可用，请刷新后重试。", true);
    return;
  }
  try {
    await updateUserPrivacyConsent("privacy_policy", {
      policyVersion: privacyPolicyVersion,
      granted: form.privacyPolicy.checked,
    });
    rememberPrivacyConsent(form.privacyPolicy.checked);
    setMessage("[data-privacy-consent-message]", "隐私同意状态已保存。");
  } catch (error) {
    setMessage("[data-privacy-consent-message]", error.message || "保存失败。", true);
  }
}

async function exportPrivacyData(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const result = await exportUserData(form.currentPassword.value);
    const blob = new Blob([JSON.stringify(result.export, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ai-nav-user-data-${currentUser.userUid || "export"}.json`;
    link.click();
    URL.revokeObjectURL(url);
    form.currentPassword.value = "";
    setMessage("[data-data-export-message]", "个人数据导出已生成。");
  } catch (error) {
    setMessage("[data-data-export-message]", error.message || "导出失败。", true);
  } finally {
    submit.disabled = false;
  }
}

async function createDeletionRequest(event) {
  event.preventDefault();
  if (!settingsVisibility.privacyWrites) return;
  const form = event.currentTarget;
  const accepted = await confirmAction({
    title: "确认申请注销账号",
    message: "申请将在等待期后软删除账号。恢复保留期结束后，个人数据将被匿名化且无法恢复。",
    confirmLabel: "提交注销申请",
  });
  if (!accepted) return;
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  try {
    const result = await requestUserDeletion({
      currentPassword: form.currentPassword.value,
      reasonCode: form.reasonCode.value,
    });
    form.currentPassword.value = "";
    renderDeletionStatus(result.request);
    setMessage("[data-deletion-message]", "注销申请已提交，可在执行前取消。");
  } catch (error) {
    setMessage("[data-deletion-message]", error.message || "提交失败。", true);
  } finally {
    submit.disabled = false;
  }
}

async function loadSessions() {
  setContentLoading("[data-session-list]", "正在读取登录设备...");
  const [sessions] = await Promise.allSettled([listUserSessions()]);
  renderSessions(sessions);
}

async function loadLearningAreas() {
  ["[data-learning-summary]", "[data-resume-box]", "[data-progress-box]", "[data-recent-box]", "[data-favorites-box]"]
    .forEach((selector) => setContentLoading(selector, "正在读取学习数据..."));
  const [dashboard, progress, recent, favorites] = await Promise.allSettled([
    getLearningDashboard(),
    listLearningProgress(),
    listRecentLearning({ page_size: 10 }),
    listLearningFavorites(),
  ]);
  renderLearningDashboard(dashboard);
  renderLearningItems("[data-progress-box]", progress, "暂无节点进度。", (item) => `
    <div class="learning-item"><div><a href="${escapeHtml(safeInternalHref(item.href, "learn.html"))}">${escapeHtml(item.title)}</a><span>${escapeHtml(item.status === "completed" ? "已完成" : item.status === "in_progress" ? "学习中" : "未开始")}</span></div><em>${item.progressPercent || 0}%</em></div>`);
  renderRecentItems(recent);
  renderLearningItems("[data-favorites-box]", favorites, "暂无收藏。", (item) => `
    <div class="learning-item"><div><a href="${escapeHtml(safeInternalHref(item.href, "learn.html"))}">${escapeHtml(item.title)}</a><span>${escapeHtml(item.description || "学习收藏")}</span></div><button class="btn subtle" type="button" data-remove-favorite="${escapeHtml(item.favoriteUid)}">移除</button></div>`);
}

function workflowToolMarkup(step) {
  const targetName = step.target?.name || step.toolNameSnapshot || "";
  if (!targetName) return '<span class="workflow-tool">无关联工具</span>';
  const href = safeInternalHref(step.target?.href, "");
  if (step.target?.status === "available" && href) {
    return `<a class="workflow-tool" href="${escapeHtml(href)}">${escapeHtml(targetName)}</a>`;
  }
  return `<span class="workflow-tool unavailable">${escapeHtml(targetName)} · 当前不可用</span>`;
}

function workflowStepsMarkup(workflow) {
  return `
    <div class="workflow-detail">
      ${workflow.description ? `<p class="workflow-description">${escapeHtml(workflow.description)}</p>` : ""}
      <ol class="workflow-step-list">
        ${workflow.steps.map((step, index) => `
          <li class="workflow-step">
            <span class="workflow-step-number" aria-hidden="true">${escapeHtml(step.stepOrder || index + 1)}</span>
            <div>
              <strong>${escapeHtml(step.name)}</strong>
              <p>${escapeHtml(step.objective)}</p>
              ${workflowToolMarkup(step)}
            </div>
          </li>`).join("")}
      </ol>
    </div>`;
}

async function loadWorkflows() {
  setContentLoading("[data-workflows-box]", "正在读取工作流...");
  const box = $("[data-workflows-box]");
  const requestedWorkflowUid = new URLSearchParams(window.location.search).get("workflow");
  try {
    const result = await listUserWorkflows({ status: "active", pageSize: 20 });
    box.setAttribute("aria-busy", "false");
    box.innerHTML = result.items.length
      ? result.items.map((item) => {
        const isTarget = item.workflowUid === requestedWorkflowUid;
        const detailId = `workflow-detail-${item.workflowUid.replaceAll(/[^a-zA-Z0-9_-]/g, "-")}`;
        return `
        <article class="learning-item workflow-item${isTarget ? " workflow-target" : ""}"
                 data-workflow-uid="${escapeHtml(item.workflowUid)}"
                 ${isTarget ? 'tabindex="-1" aria-label="刚保存的工作流，步骤详情已展开"' : ""}>
          <div class="workflow-overview">
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.description || "已保存工作流")} · ${item.steps.length} 步 · ${item.availability.status === "degraded" ? "部分工具不可用" : "可用"}</span>
          </div>
          <div class="workflow-actions">
            <button class="btn subtle" type="button"
                    data-workflow-detail-toggle="${escapeHtml(item.workflowUid)}"
                    aria-expanded="${String(isTarget)}"
                    aria-controls="${escapeHtml(detailId)}">${isTarget ? "收起步骤" : "查看步骤"}</button>
            <button class="btn subtle" type="button" data-archive-workflow="${escapeHtml(item.workflowUid)}" data-workflow-version="${item.version}">归档</button>
          </div>
          <div id="${escapeHtml(detailId)}" class="workflow-detail-region" ${isTarget ? "" : "hidden"}>
            ${workflowStepsMarkup(item)}
          </div>
        </article>`;
      }).join("")
      : stateBlock("暂无已保存工作流。");
    const target = [...box.querySelectorAll("[data-workflow-uid]")]
      .find((item) => item.dataset.workflowUid === requestedWorkflowUid);
    if (target) {
      target.focus({ preventScroll: true });
      target.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  } catch (error) {
    box.setAttribute("aria-busy", "false");
    box.innerHTML = stateBlock(error.message || "工作流暂不可用。", "workflows");
  }
}

function learningHistoryItem(item) {
  const time = item.lastReadAt || item.lastStudiedAt || item.updatedAt;
  const detail = time ? formatLearningTime(time) : item.description || "最近阅读";
  return `<div class="learning-item"><div><a href="${escapeHtml(safeInternalHref(item.href, "learn.html"))}">${escapeHtml(item.title)}</a><span title="${escapeHtml(learningTimeTitle(time))}">${escapeHtml(detail)}</span></div><em>继续</em></div>`;
}

function renderLearningItems(selector, result, emptyText, template) {
  const box = $(selector);
  box.setAttribute("aria-busy", "false");
  if (result.status !== "fulfilled") {
    box.innerHTML = stateBlock("学习数据暂不可用。", "learning");
    return;
  }
  const items = result.value.items || [];
  box.innerHTML = items.length ? items.map(template).join("") : stateBlock(emptyText);
}

function renderRecentItems(result, append = false) {
  const box = $("[data-recent-box]");
  box.setAttribute("aria-busy", "false");
  if (result.status !== "fulfilled") {
    box.innerHTML = stateBlock("学习数据暂不可用。", "learning");
    return;
  }
  const items = result.value.items || [];
  const currentButton = box.querySelector("[data-load-recent]");
  currentButton?.remove();
  if (!append) box.innerHTML = items.length ? items.map(learningHistoryItem).join("") : stateBlock("暂无最近阅读。");
  else box.insertAdjacentHTML("beforeend", items.map(learningHistoryItem).join(""));
  if (result.value.meta?.hasNext) {
    const nextPage = Number(result.value.meta.page || 1) + 1;
    box.insertAdjacentHTML("beforeend", `<button class="btn subtle" type="button" data-load-recent="${nextPage}">加载更多</button>`);
    box.querySelector("[data-load-recent]").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      button.textContent = "正在加载...";
      try {
        const page = Number(button.dataset.loadRecent);
        renderRecentItems({ status: "fulfilled", value: await listRecentLearning({ page, page_size: 10 }) }, true);
      } catch {
        button.disabled = false;
        button.textContent = "加载失败，重试";
      }
    });
  }
}

function renderLearningDashboard(result) {
  const summary = $("[data-learning-summary]");
  const resume = $("[data-resume-box]");
  summary.setAttribute("aria-busy", "false");
  resume.setAttribute("aria-busy", "false");
  if (result.status !== "fulfilled") {
    summary.innerHTML = stateBlock("学习概览暂不可用。", "learning");
    resume.innerHTML = stateBlock("继续学习暂不可用。", "learning");
    return;
  }
  const data = result.value;
  summary.innerHTML = `
    <div><strong>${data.summary.startedCount}</strong><span>学习中</span></div>
    <div><strong>${data.summary.completedCount}</strong><span>已完成</span></div>
    <div><strong>${data.summary.overallPercent}%</strong><span>平均进度</span></div>`;
  resume.innerHTML = data.resume ? learningHistoryItem(data.resume) : stateBlock("暂无继续学习目标。");
}

function renderReserved(selector, result, label) {
  const box = $(selector);
  box.setAttribute("aria-busy", "false");
  if (result.status !== "fulfilled") {
    box.innerHTML = stateBlock(`${label}接口暂不可用。`, "workflows");
    return;
  }
  const items = result.value.items || [];
  if (!items.length) {
    box.innerHTML = stateBlock(result.value.meta?.message || `${label}暂无数据。`);
    return;
  }
  box.innerHTML = items.map((item) => `<div>${escapeHtml(item.title || item.name || item.workflowUid || item.nodeSlug)}</div>`).join("");
}

function renderSessions(result) {
  const box = $("[data-session-list]");
  box.setAttribute("aria-busy", "false");
  if (result.status !== "fulfilled") {
    box.innerHTML = stateBlock("登录设备接口暂不可用。", "sessions");
    return;
  }
  const items = result.value.items || [];
  if (!items.length) {
    box.innerHTML = stateBlock("暂无登录设备。");
    return;
  }
  const riskLabel = {
    normal: "",
    ended: "已结束",
    medium: "需关注",
    high: "高风险",
  };
  box.innerHTML = items.map((item) => `
    <div class="session-item">
      <div><strong>${escapeHtml(item.deviceName || "未知设备")}${item.isCurrent ? "（当前设备）" : item.isRevoked ? "（已退出）" : ""}</strong><span>${escapeHtml(item.ipAddress || "未知 IP")} · ${escapeHtml(item.lastSeenAt || item.createdAt || "")}${riskLabel[item.riskLevel] ? ` · ${escapeHtml(riskLabel[item.riskLevel])}` : ""}</span></div>
      ${item.isRevoked || item.isCurrent ? "" : `<button class="btn danger" data-revoke-session="${escapeHtml(item.sessionUid)}" type="button">撤销</button>`}
    </div>`).join("");
}

async function saveProfile(event) {
  event.preventDefault();
  setFormState("profile", "saving", "正在保存资料...");
  try {
    const data = await updateUserProfile({
      ...Object.fromEntries(new FormData(event.currentTarget).entries()),
      expectedVersion: profileVersion,
    });
    profileVersion = data.profile.version;
    $("[data-user-display]").textContent = data.profile.displayName || currentUser?.username || "用户设置";
    renderAvatar(data.profile.avatarUrl, true);
    setFormState("profile", "success", "资料已保存。");
  } catch (err) {
    if (err.status === 409 && err.code === "PROFILE_VERSION_CONFLICT") {
      const latest = await getUserProfile().catch(() => null);
      if (latest) profileVersion = latest.profile.version;
      setFormState("profile", "error", "资料已在其他页面更新。当前输入已保留，请检查后再次保存。");
      return;
    }
    setFormState("profile", "error", err.message || "保存失败");
  }
}

async function saveAccount(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const body = Object.fromEntries(new FormData(form).entries());
  if (!body.currentPassword) delete body.currentPassword;
  const contactsChanged = !accountSnapshot
    || body.email.trim().toLowerCase() !== (accountSnapshot.email || "").toLowerCase()
    || body.phone.trim() !== (accountSnapshot.phone || "");
  if (!await confirmAction({
    title: "确认保存账号",
    message: contactsChanged
      ? "邮箱或手机号变更后验证状态会重置，并立即成为新的登录标识。"
      : "用户名会立即更新，并影响你的公开账号标识。",
    confirmLabel: "确认保存",
  })) return;
  setFormState("account", "saving", "正在保存账号...");
  try {
    const data = await updateUserAccount(body);
    accountSnapshot = data.account;
    currentUser = {
      ...currentUser,
      username: data.account.username,
      email: data.account.email,
      phone: data.account.phone,
    };
    $("[data-user-name]").textContent = `@${data.account.username || "user"}`;
    form.email.value = data.account.email || "";
    form.phone.value = data.account.phone || "";
    form.currentPassword.value = "";
    $("[data-account-email-status]").textContent = data.account.email
      ? `当前状态：${data.account.emailVerified ? "已验证" : "未验证"}`
      : "尚未绑定邮箱";
    $("[data-account-phone-status]").textContent = data.account.phone
      ? `当前状态：${data.account.phoneVerified ? "已验证" : "未验证"}`
      : "尚未绑定手机号";
    setFormState("account", "success", "账号信息已保存。");
  } catch (err) {
    setFormState("account", "error", err.message || "保存失败");
  }
}

async function savePassword(event) {
  event.preventDefault();
  if (!await confirmAction({
    title: "确认修改密码",
    message: "修改后当前登录状态会退出，需要使用新密码重新登录。",
    confirmLabel: "修改并退出",
  })) return;
  setFormState("password", "saving", "正在修改密码...");
  try {
    await updateUserPassword(Object.fromEntries(new FormData(event.currentTarget).entries()));
    clearAuthTokens();
    setFormState("password", "loading", "密码已修改，请重新登录。");
    window.setTimeout(() => {
      window.location.href = "index.html";
    }, 900);
  } catch (err) {
    setFormState("password", "error", err.message || "修改失败");
  }
}

async function saveSecurityQuestions(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const items = [0, 1, 2].map((index) => ({
    question: form[`question${index}`].value,
    answer: form[`answer${index}`].value,
  }));
  if (!await confirmAction({
    title: "确认更新密保问题",
    message: "新的问题和答案将覆盖当前密保设置。",
    confirmLabel: "确认更新",
  })) return;
  setFormState("security", "saving", "正在保存密保问题...");
  try {
    const data = await updateUserSecurityQuestions({
      currentPassword: form.currentPassword.value,
      items,
    });
    form.currentPassword.value = "";
    [0, 1, 2].forEach((index) => {
      form[`answer${index}`].value = "";
    });
    $("[data-security-status]").textContent = `已设置 ${data.items.length} 个密保问题。修改时需要重新填写答案。`;
    fillQuestionRows(data.items);
    setFormState("security", "success", "密保问题已保存。");
  } catch (err) {
    setFormState("security", "error", err.message || "保存失败");
  }
}

async function savePreferences(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setFormState("preferences", "saving", "正在保存偏好...");
  try {
    const data = await updateUserPreferences({
      expectedVersion: preferencesVersion,
      cnFirst: form.cnFirst.checked,
      freeFirst: form.freeFirst.checked,
      showExternalResources: form.showExternalResources.checked,
    });
    preferencesVersion = data.preferences.version;
    if (form.agentMemoryEnabled.checked !== agentMemoryConsentGranted) {
      if (!agentMemoryPolicyVersion) throw new Error("Agent memory 同意版本不可用，请刷新后重试。");
      await updateUserPrivacyConsent("agent_memory", {
        policyVersion: agentMemoryPolicyVersion,
        granted: form.agentMemoryEnabled.checked,
      });
      agentMemoryConsentGranted = form.agentMemoryEnabled.checked;
    }
    setFormState("preferences", "success", "偏好已保存。");
  } catch (err) {
    if (err.status === 409 && err.code === "PREFERENCES_VERSION_CONFLICT") {
      const latest = await getUserPreferences().catch(() => null);
      if (latest) preferencesVersion = latest.preferences.version;
      setFormState("preferences", "error", "偏好已在其他页面更新。当前选择已保留，请检查后再次保存。");
      return;
    }
    setFormState("preferences", "error", err.message || "保存失败");
  }
}

function resetCrop() {
  const wasOpen = $("[data-crop-panel]").classList.contains("open");
  cropState = null;
  const panel = $("[data-crop-panel]");
  panel.classList.remove("open");
  panel.setAttribute("aria-hidden", "true");
  const input = $("[data-avatar-input]");
  if (input) input.value = "";
  if (wasOpen) window.setTimeout(() => cropReturnFocus?.focus?.(), 0);
  cropReturnFocus = null;
}

function cropMetrics() {
  const canvas = $("[data-crop-canvas]");
  const size = canvas.width;
  const radius = size * CROP_RADIUS_RATIO;
  const scale = cropState.baseScale * cropState.zoom;
  const width = cropState.image.width * scale;
  const height = cropState.image.height * scale;
  const x = size / 2 - width / 2 + cropState.offsetX;
  const y = size / 2 - height / 2 + cropState.offsetY;
  return { size, radius, scale, width, height, x, y };
}

function clampCrop() {
  if (!cropState) return;
  const { size, radius, width, height } = cropMetrics();
  const minX = size / 2 + radius - width;
  const maxX = size / 2 - radius;
  const minY = size / 2 + radius - height;
  const maxY = size / 2 - radius;
  const currentX = size / 2 - width / 2 + cropState.offsetX;
  const currentY = size / 2 - height / 2 + cropState.offsetY;
  const clampedX = Math.min(maxX, Math.max(minX, currentX));
  const clampedY = Math.min(maxY, Math.max(minY, currentY));
  cropState.offsetX += clampedX - currentX;
  cropState.offsetY += clampedY - currentY;
}

function drawCrop() {
  if (!cropState) return;
  clampCrop();
  const canvas = $("[data-crop-canvas]");
  const ctx = canvas.getContext("2d");
  const { size, radius, width, height, x, y } = cropMetrics();
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = "#f6f8fa";
  ctx.fillRect(0, 0, size, size);
  ctx.drawImage(cropState.image, x, y, width, height);
  ctx.save();
  ctx.fillStyle = "rgba(87,96,106,.42)";
  ctx.fillRect(0, 0, size, size);
  ctx.globalCompositeOperation = "destination-out";
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
  ctx.strokeStyle = "rgba(255,255,255,.96)";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, radius, 0, Math.PI * 2);
  ctx.stroke();
}

function startCropDrag(event) {
  if (!cropState) return;
  cropState.dragging = true;
  cropState.startX = event.clientX;
  cropState.startY = event.clientY;
  cropState.startOffsetX = cropState.offsetX;
  cropState.startOffsetY = cropState.offsetY;
  event.currentTarget.setPointerCapture(event.pointerId);
}

function moveCropDrag(event) {
  if (!cropState?.dragging) return;
  const canvas = $("[data-crop-canvas]");
  const ratio = canvas.width / canvas.getBoundingClientRect().width;
  cropState.offsetX = cropState.startOffsetX + (event.clientX - cropState.startX) * ratio;
  cropState.offsetY = cropState.startOffsetY + (event.clientY - cropState.startY) * ratio;
  drawCrop();
}

function endCropDrag() {
  if (cropState) cropState.dragging = false;
}

async function prepareAvatarCrop(event) {
  const input = event.currentTarget;
  const file = input.files?.[0];
  setMessage("[data-avatar-message]", "");
  if (!file) return;
  if (file.size > MAX_AVATAR_BYTES) {
    setMessage("[data-avatar-message]", "头像原图不能超过 2MB。", true);
    input.value = "";
    return;
  }
  if (!ALLOWED_AVATAR_TYPES.has(file.type)) {
    setMessage("[data-avatar-message]", "仅支持 JPG、PNG、WebP 或 GIF 图片。", true);
    input.value = "";
    return;
  }
  const image = new Image();
  const objectUrl = URL.createObjectURL(file);
  image.onload = () => {
    URL.revokeObjectURL(objectUrl);
    if (image.width * image.height > MAX_AVATAR_SOURCE_PIXELS) {
      setMessage("[data-avatar-message]", "图片像素尺寸过大，请选择更小的图片。", true);
      input.value = "";
      return;
    }
    const size = 512;
    const radius = size * CROP_RADIUS_RATIO;
    cropState = {
      image,
      zoom: 1,
      baseScale: Math.max((radius * 2) / image.width, (radius * 2) / image.height),
      offsetX: 0,
      offsetY: 0,
      dragging: false,
      pinchDistance: 0,
      pinchZoom: 1,
    };
    cropReturnFocus = input;
    const panel = $("[data-crop-panel]");
    panel.classList.add("open");
    panel.setAttribute("aria-hidden", "false");
    $("[data-crop-zoom]").value = "1";
    drawCrop();
    $("[data-crop-confirm]").focus();
  };
  image.onerror = () => {
    URL.revokeObjectURL(objectUrl);
    input.value = "";
    setMessage("[data-avatar-message]", "无法读取图片。", true);
  };
  image.src = objectUrl;
}

async function confirmAvatarCrop() {
  setMessage("[data-crop-message]", "");
  if (!cropState) return;
  const cropBody = $("[data-crop-panel] .crop-body");
  const confirmButton = $("[data-crop-confirm]");
  const idleLabel = confirmButton.textContent;
  cropBody.setAttribute("aria-busy", "true");
  confirmButton.disabled = true;
  confirmButton.textContent = "上传中...";
  try {
    const output = document.createElement("canvas");
    output.width = 512;
    output.height = 512;
    const ctx = output.getContext("2d");
    clampCrop();
    const { size, radius, scale, x, y } = cropMetrics();
    const sourceX = (size / 2 - radius - x) / scale;
    const sourceY = (size / 2 - radius - y) / scale;
    const sourceSize = (radius * 2) / scale;
    ctx.beginPath();
    ctx.arc(256, 256, 256, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(cropState.image, sourceX, sourceY, sourceSize, sourceSize, 0, 0, 512, 512);
    const blob = await new Promise((resolve) => output.toBlob(resolve, "image/webp", 0.9));
    if (!blob) {
      setMessage("[data-crop-message]", "头像生成失败。", true);
      return;
    }
    const body = new FormData();
    body.append("file", blob, "avatar.webp");
    const data = await uploadUserAvatar(body);
    profileVersion = data.profile.version;
    renderAvatar(data.avatarUrl, true);
    resetCrop();
    setMessage("[data-avatar-message]", "头像已上传并压缩。");
  } catch (err) {
    setMessage("[data-crop-message]", err.message || "上传失败", true);
  } finally {
    cropBody.setAttribute("aria-busy", "false");
    confirmButton.disabled = false;
    confirmButton.textContent = idleLabel;
  }
}

function setCropZoom(nextZoom) {
  if (!cropState) return;
  cropState.zoom = Math.min(3, Math.max(1, nextZoom));
  const range = $("[data-crop-zoom]");
  if (range) range.value = String(cropState.zoom);
  drawCrop();
}

function handleCropWheel(event) {
  if (!cropState) return;
  event.preventDefault();
  const delta = event.deltaY > 0 ? -0.06 : 0.06;
  setCropZoom(cropState.zoom + delta);
}

function touchDistance(touches) {
  const [a, b] = touches;
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

function startCropTouch(event) {
  if (!cropState || event.touches.length !== 2) return;
  cropState.pinchDistance = touchDistance(event.touches);
  cropState.pinchZoom = cropState.zoom;
}

function moveCropTouch(event) {
  if (!cropState || event.touches.length !== 2 || !cropState.pinchDistance) return;
  event.preventDefault();
  const ratio = touchDistance(event.touches) / cropState.pinchDistance;
  setCropZoom(cropState.pinchZoom * ratio);
}

async function logout() {
  try {
    await logoutUser();
  } catch {
    // Local logout should not be blocked by an expired server session.
  }
  clearAuthTokens();
  window.location.href = "index.html";
}

async function retryArea(area) {
  const loaders = {
    account: () => loadAccountDetails(),
    profile: () => loadProfile(),
    preferences: () => loadPreferences(),
    privacy: () => loadPrivacy(),
    security: () => loadSecurityQuestions(),
    sessions: () => loadSessions(),
    learning: () => loadLearningAreas(),
    workflows: () => loadWorkflows(),
  };
  await loaders[area]?.();
}

async function init() {
  const user = requireLogin(await initAuthUI());
  if (!user) {
    renderLoginRequired();
    return;
  }
  $("[data-settings-login-required]").hidden = true;
  $("[data-settings-content]").hidden = false;
  applyPublicSettingsCapabilities(null);
  currentUser = user;
  wireFormLabels();
  await loadPublicSettingsCapabilities();
  showSection(window.location.hash.slice(1) || "profile");
  if (settingsVisibility.passwordChanges) setFormState("password", "idle");
  await loadAccount(user);
  await loadAtomicAreas();

  window.addEventListener("hashchange", () => showSection(window.location.hash.slice(1) || "profile"));
  $("[data-profile-form]").addEventListener("submit", saveProfile);
  if (settingsVisibility.identityChanges) {
    $("[data-account-form]").addEventListener("submit", saveAccount);
  }
  if (settingsVisibility.passwordChanges) {
    $("[data-password-form]").addEventListener("submit", savePassword);
  }
  if (settingsVisibility.recovery) {
    $("[data-security-form]").addEventListener("submit", saveSecurityQuestions);
  }
  $("[data-preferences-form]").addEventListener("submit", savePreferences);
  if (settingsVisibility.privacyWrites) {
    $("[data-privacy-consent-form] [name='privacyPolicy']").addEventListener("change", savePrivacyConsent);
    $("[data-deletion-form]")?.addEventListener("submit", createDeletionRequest);
  }
  $("[data-settings-legal]").addEventListener("click", (event) => {
    event.preventDefault();
    $("[data-settings-legal-dialog]").showModal();
  });
  $("[data-settings-legal-close]").addEventListener("click", () => $("[data-settings-legal-dialog]").close());
  $("[data-avatar-input]").addEventListener("change", prepareAvatarCrop);
  $all("[data-crop-close]").forEach((button) => button.addEventListener("click", resetCrop));
  $("[data-crop-confirm]").addEventListener("click", confirmAvatarCrop);
  $("[data-crop-zoom]").addEventListener("input", (event) => {
    if (!cropState) return;
    cropState.zoom = Number(event.currentTarget.value);
    drawCrop();
  });
  const canvas = $("[data-crop-canvas]");
  canvas.addEventListener("pointerdown", startCropDrag);
  canvas.addEventListener("pointermove", moveCropDrag);
  canvas.addEventListener("pointerup", endCropDrag);
  canvas.addEventListener("pointercancel", endCropDrag);
  canvas.addEventListener("wheel", handleCropWheel, { passive: false });
  canvas.addEventListener("touchstart", startCropTouch, { passive: false });
  canvas.addEventListener("touchmove", moveCropTouch, { passive: false });
  document.addEventListener("click", async (event) => {
    const workflowDetailToggle = event.target.closest("[data-workflow-detail-toggle]");
    if (workflowDetailToggle) {
      const detail = document.getElementById(workflowDetailToggle.getAttribute("aria-controls"));
      const expanded = workflowDetailToggle.getAttribute("aria-expanded") === "true";
      workflowDetailToggle.setAttribute("aria-expanded", String(!expanded));
      workflowDetailToggle.textContent = expanded ? "查看步骤" : "收起步骤";
      if (detail) detail.hidden = expanded;
      return;
    }

    const retry = event.target.closest("[data-retry-area]");
    if (retry) {
      retry.disabled = true;
      await retryArea(retry.dataset.retryArea);
      return;
    }
    const revoke = event.target.closest("[data-revoke-session]");
    if (revoke) {
      const accepted = await confirmAction({
        title: "确认撤销登录设备",
        message: "该设备的刷新会话将立即失效。",
        confirmLabel: "确认撤销",
      });
      if (!accepted) return;
      revoke.disabled = true;
      revoke.textContent = "撤销中...";
      try {
        await revokeUserSession(revoke.dataset.revokeSession);
        await loadSessions();
      } catch (error) {
        $("[data-session-list]").innerHTML = stateBlock(error.message || "撤销会话失败。", "sessions");
      }
    }
    const revokeOthers = event.target.closest("[data-revoke-other-sessions]");
    if (revokeOthers) {
      const accepted = await confirmAction({
        title: "确认退出其他设备",
        message: "除当前设备外，其他有效登录会话都将被撤销。",
        confirmLabel: "退出其他设备",
      });
      if (!accepted) return;
      revokeOthers.disabled = true;
      const idleLabel = revokeOthers.textContent;
      revokeOthers.textContent = "正在退出...";
      try {
        await revokeOtherUserSessions();
        await loadSessions();
      } catch (error) {
        $("[data-session-list]").innerHTML = stateBlock(error.message || "退出其他设备失败。", "sessions");
      } finally {
        revokeOthers.disabled = false;
        revokeOthers.textContent = idleLabel;
      }
    }
    const favorite = event.target.closest("[data-remove-favorite]");
    if (favorite) {
      favorite.disabled = true;
      favorite.textContent = "移除中...";
      try {
        await removeLearningFavorite(favorite.dataset.removeFavorite);
        await loadLearningAreas();
      } catch (error) {
        $("[data-favorites-box]").innerHTML = stateBlock(error.message || "移除收藏失败。", "learning");
      }
    }
    const archiveWorkflow = event.target.closest("[data-archive-workflow]");
    if (archiveWorkflow) {
      const accepted = await confirmAction({
        title: "归档工作流",
        message: "工作流会从当前列表移出，但仍可恢复。",
        confirmLabel: "确认归档",
      });
      if (!accepted) return;
      archiveWorkflow.disabled = true;
      try {
        await archiveUserWorkflow(
          archiveWorkflow.dataset.archiveWorkflow,
          Number(archiveWorkflow.dataset.workflowVersion),
        );
        await loadWorkflows();
      } catch (error) {
        $("[data-workflows-box]").innerHTML = stateBlock(error.message || "归档失败。", "workflows");
      }
    }
    const cancelDeletion = event.target.closest("[data-cancel-deletion]");
    if (cancelDeletion) {
      if (!settingsVisibility.privacyWrites) return;
      const accepted = await confirmAction({
        title: "取消注销申请",
        message: "账号将继续保持正常使用。",
        confirmLabel: "确认取消",
      });
      if (!accepted) return;
      cancelDeletion.disabled = true;
      try {
        await cancelUserDeletion(cancelDeletion.dataset.cancelDeletion);
        renderDeletionStatus(null);
        setMessage("[data-deletion-message]", "注销申请已取消。");
      } catch (error) {
        setMessage("[data-deletion-message]", error.message || "取消失败。", true);
        cancelDeletion.disabled = false;
      }
    }
    if (event.target.closest("[data-logout]")) await logout();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && cropState) resetCrop();
  });
}

if (typeof document !== "undefined") init();
