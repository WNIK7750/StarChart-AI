import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiPut,
  apiUpload,
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
} from "./api.js";

const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
let cropState = null;
const CROP_RADIUS_RATIO = 0.39;

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
}

function absoluteUrl(url = "") {
  if (!url) return "";
  if (/^https?:\/\//.test(url)) return url;
  return url;
}

function showSection(name = "profile") {
  const sectionName = name || "profile";
  $all("[data-section]").forEach((section) => {
    section.classList.toggle("active", section.dataset.section === sectionName);
  });
  $all("[data-section-link]").forEach((link) => {
    link.classList.toggle("active", link.getAttribute("href") === `#${sectionName}`);
  });
}

function renderAvatar(url) {
  const src = absoluteUrl(url);
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
}

async function requireLogin() {
  if (!getAccessToken()) {
    window.location.href = "index.html";
    return null;
  }
  try {
    const data = await apiGet("/auth/me");
    return data.user;
  } catch {
    clearAuthTokens();
    window.location.href = "index.html";
    return null;
  }
}

async function loadAccount(user) {
  const [accountResult, profileResult, prefsResult, securityResult] = await Promise.allSettled([
    apiGet("/users/me/account"),
    apiGet("/users/me/profile"),
    apiGet("/users/me/preferences"),
    apiGet("/users/me/security-questions"),
  ]);

  if (accountResult.status === "fulfilled") {
    $("[data-account-form] [name='username']").value = accountResult.value.account.username || user.username || "";
    $("[data-user-name]").textContent = `@${accountResult.value.account.username || user.username || "user"}`;
  }
  if (profileResult.status === "fulfilled") {
    const profile = profileResult.value.profile;
    const form = $("[data-profile-form]");
    form.displayName.value = profile.displayName || "";
    form.learningLevel.value = profile.learningLevel || "beginner";
    form.targetDirection.value = profile.targetDirection || "";
    form.bio.value = profile.bio || "";
    $("[data-user-display]").textContent = profile.displayName || user.username || "用户设置";
    renderAvatar(profile.avatarUrl);
  } else {
    renderAvatar("");
  }
  if (prefsResult.status === "fulfilled") {
    const prefs = prefsResult.value.preferences;
    const form = $("[data-preferences-form]");
    form.cnFirst.checked = Boolean(prefs.cnFirst);
    form.freeFirst.checked = Boolean(prefs.freeFirst);
    form.showExternalResources.checked = Boolean(prefs.showExternalResources);
    form.agentMemoryEnabled.checked = Boolean(prefs.agentMemoryEnabled);
  }
  if (securityResult.status === "fulfilled") {
    const data = securityResult.value;
    $("[data-security-status]").textContent = data.configured
      ? `已设置 ${data.items.length} 个密保问题。修改时需要重新填写答案。`
      : "尚未设置密保问题。设置后可在登录页找回密码。";
    fillQuestionRows(data.items);
  } else {
    $("[data-security-status]").textContent = "密保接口暂不可用，请稍后再试。";
    fillQuestionRows();
  }
}

async function loadAtomicAreas() {
  const [sessions, progress, favorites, workflows] = await Promise.allSettled([
    apiGet("/users/me/sessions"),
    apiGet("/users/me/learning/progress"),
    apiGet("/users/me/favorites"),
    apiGet("/users/me/workflows"),
  ]);
  renderSessions(sessions);
  renderReserved("[data-progress-box]", progress, "学习记录");
  renderReserved("[data-favorites-box]", favorites, "收藏");
  renderReserved("[data-workflows-box]", workflows, "工作流");
}

function renderReserved(selector, result, label) {
  const box = $(selector);
  if (result.status !== "fulfilled") {
    box.textContent = `${label}接口暂不可用。`;
    return;
  }
  const items = result.value.items || [];
  if (!items.length) {
    box.textContent = result.value.meta?.message || `${label}暂无数据，已保留后端接口。`;
    return;
  }
  box.innerHTML = items.map((item) => `<div>${escapeHtml(item.title || item.name || item.workflowUid || item.nodeSlug)}</div>`).join("");
}

function renderSessions(result) {
  const box = $("[data-session-list]");
  if (result.status !== "fulfilled") {
    box.innerHTML = '<div class="reserved">登录设备接口暂不可用。</div>';
    return;
  }
  const items = result.value.items || [];
  if (!items.length) {
    box.innerHTML = '<div class="reserved">暂无登录设备。</div>';
    return;
  }
  box.innerHTML = items.map((item) => `
    <div class="session-item">
      <div><strong>${escapeHtml(item.deviceName || "未知设备")}${item.isRevoked ? "（已退出）" : ""}</strong><span>${escapeHtml(item.ipAddress || "未知 IP")} · ${escapeHtml(item.lastSeenAt || item.createdAt || "")}</span></div>
      ${item.isRevoked ? "" : `<button class="btn danger" data-revoke-session="${escapeHtml(item.sessionUid)}" type="button">撤销</button>`}
    </div>`).join("");
}

async function saveProfile(event) {
  event.preventDefault();
  setMessage("[data-profile-message]", "");
  try {
    await apiPatch("/users/me/profile", Object.fromEntries(new FormData(event.currentTarget).entries()));
    setMessage("[data-profile-message]", "资料已保存。");
    await loadAccount(await apiGet("/auth/me").then((data) => data.user));
  } catch (err) {
    setMessage("[data-profile-message]", err.message || "保存失败", true);
  }
}

async function saveAccount(event) {
  event.preventDefault();
  setMessage("[data-account-message]", "");
  try {
    await apiPatch("/users/me/account", Object.fromEntries(new FormData(event.currentTarget).entries()));
    setMessage("[data-account-message]", "用户名已保存。");
    await loadAccount(await apiGet("/auth/me").then((data) => data.user));
  } catch (err) {
    setMessage("[data-account-message]", err.message || "保存失败", true);
  }
}

async function savePassword(event) {
  event.preventDefault();
  setMessage("[data-password-message]", "");
  try {
    await apiPatch("/users/me/password", Object.fromEntries(new FormData(event.currentTarget).entries()));
    clearAuthTokens();
    setMessage("[data-password-message]", "密码已修改，请重新登录。");
    window.setTimeout(() => {
      window.location.href = "index.html";
    }, 900);
  } catch (err) {
    setMessage("[data-password-message]", err.message || "修改失败", true);
  }
}

async function saveSecurityQuestions(event) {
  event.preventDefault();
  setMessage("[data-security-message]", "");
  const form = event.currentTarget;
  const items = [0, 1, 2].map((index) => ({
    question: form[`question${index}`].value,
    answer: form[`answer${index}`].value,
  }));
  try {
    const data = await apiPut("/users/me/security-questions", {
      currentPassword: form.currentPassword.value,
      items,
    });
    form.currentPassword.value = "";
    [0, 1, 2].forEach((index) => {
      form[`answer${index}`].value = "";
    });
    $("[data-security-status]").textContent = `已设置 ${data.items.length} 个密保问题。修改时需要重新填写答案。`;
    fillQuestionRows(data.items);
    setMessage("[data-security-message]", "密保问题已保存。");
  } catch (err) {
    setMessage("[data-security-message]", err.message || "保存失败", true);
  }
}

async function savePreferences(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setMessage("[data-preferences-message]", "");
  try {
    await apiPatch("/users/me/preferences", {
      cnFirst: form.cnFirst.checked,
      freeFirst: form.freeFirst.checked,
      showExternalResources: form.showExternalResources.checked,
      agentMemoryEnabled: form.agentMemoryEnabled.checked,
    });
    setMessage("[data-preferences-message]", "偏好已保存。");
  } catch (err) {
    setMessage("[data-preferences-message]", err.message || "保存失败", true);
  }
}

function resetCrop() {
  cropState = null;
  $("[data-crop-panel]").classList.remove("open");
  const input = $("[data-avatar-input]");
  if (input) input.value = "";
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
  if (!file.type.startsWith("image/")) {
    setMessage("[data-avatar-message]", "请选择图片文件。", true);
    input.value = "";
    return;
  }
  const image = new Image();
  image.onload = () => {
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
    $("[data-crop-panel]").classList.add("open");
    $("[data-crop-zoom]").value = "1";
    drawCrop();
  };
  image.onerror = () => setMessage("[data-avatar-message]", "无法读取图片。", true);
  image.src = URL.createObjectURL(file);
}

async function confirmAvatarCrop() {
  setMessage("[data-crop-message]", "");
  if (!cropState) return;
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
  try {
    const body = new FormData();
    body.append("file", blob, "avatar.webp");
    const data = await apiUpload("/users/me/avatar", body);
    renderAvatar(data.avatarUrl);
    resetCrop();
    setMessage("[data-avatar-message]", "头像已上传并压缩。");
  } catch (err) {
    setMessage("[data-crop-message]", err.message || "上传失败", true);
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
    const refreshToken = getRefreshToken();
    if (refreshToken) await apiPost("/auth/logout", { refreshToken });
  } catch {
    // Local logout should not be blocked by an expired server session.
  }
  clearAuthTokens();
  window.location.href = "index.html";
}

async function init() {
  const user = await requireLogin();
  if (!user) return;
  showSection(window.location.hash.slice(1) || "profile");
  await loadAccount(user);
  await loadAtomicAreas();

  window.addEventListener("hashchange", () => showSection(window.location.hash.slice(1) || "profile"));
  $("[data-profile-form]").addEventListener("submit", saveProfile);
  $("[data-account-form]").addEventListener("submit", saveAccount);
  $("[data-password-form]").addEventListener("submit", savePassword);
  $("[data-security-form]").addEventListener("submit", saveSecurityQuestions);
  $("[data-preferences-form]").addEventListener("submit", savePreferences);
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
    const revoke = event.target.closest("[data-revoke-session]");
    if (revoke) {
      await apiDelete(`/users/me/sessions/${encodeURIComponent(revoke.dataset.revokeSession)}`);
      await loadAtomicAreas();
    }
    if (event.target.closest("[data-logout]")) await logout();
  });
}

init();
