const STYLE_ID = "shared-ui-feedback-styles";

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .ui-feedback{min-height:112px;width:100%;display:grid;place-items:center;align-content:center;gap:7px;padding:22px;text-align:center;color:#57606a;background:#fff;border:1px solid rgba(15,15,25,.09);border-radius:8px}
    .ui-feedback strong{color:#24292f;font-size:14px}.ui-feedback p{max-width:520px;margin:0;font-size:12px;line-height:1.65}.ui-feedback button{height:34px;margin-top:4px;padding:0 12px;border:1px solid rgba(15,15,25,.12);border-radius:7px;background:#fff;color:#24292f;font-size:12px;font-weight:700}
    .ui-feedback button:hover{background:#f6f8fa}.ui-feedback--loading::before{content:"";width:16px;height:16px;border:2px solid #d0d7de;border-top-color:#6d5ef6;border-radius:50%;animation:ui-feedback-spin .8s linear infinite}.ui-feedback--error strong,.ui-feedback--offline strong{color:#b42318}
    .ui-feedback--compact{min-height:72px;padding:14px}.ui-feedback--compact p{font-size:12px}@keyframes ui-feedback-spin{to{transform:rotate(360deg)}}
    @media(prefers-reduced-motion:reduce){.ui-feedback--loading::before{animation:none}}
  `;
  document.head.appendChild(style);
}

export function feedbackKindForError(error) {
  if (error?.code === "API_OFFLINE") return "offline";
  return "error";
}

export function feedbackMarkup({
  kind = "empty",
  title = "",
  message = "",
  actionLabel = "",
  actionKey = "",
  compact = false,
  className = "",
} = {}) {
  injectStyles();
  const role = ["error", "offline"].includes(kind) ? "alert" : "status";
  const action = actionLabel
    ? `<button type="button" data-feedback-action="${escapeHtml(actionKey)}">${escapeHtml(actionLabel)}</button>`
    : "";
  return `<div class="ui-feedback ui-feedback--${escapeHtml(kind)}${compact ? " ui-feedback--compact" : ""}${className ? ` ${escapeHtml(className)}` : ""}" role="${role}">${title ? `<strong>${escapeHtml(title)}</strong>` : ""}${message ? `<p>${escapeHtml(message)}</p>` : ""}${action}</div>`;
}

export function renderFeedback(container, options = {}) {
  if (!container) return null;
  container.innerHTML = feedbackMarkup(options);
  const action = container.querySelector("[data-feedback-action]");
  if (action && options.onAction) action.addEventListener("click", options.onAction);
  return action;
}
