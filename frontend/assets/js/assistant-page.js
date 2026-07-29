import {
  ApiError,
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiPostStream,
  getAccessToken,
} from "./api.js";
import { consumeAgentEventStream } from "./agent-sse.js";
import { AssistantSessionEpoch } from "./assistant-session-epoch.js";
import { createFrameBuffer } from "./page-shell.js";
import { safeInternalHref } from "./url-safety.js";
import {
  appendGuestMessage,
  clearGuestConversations,
  createGuestConversation,
  loadGuestConversations,
  recentGuestHistory,
} from "./guest-agent-memory.js";
import { saveAgentWorkflow } from "./users-api.js";

const form = document.querySelector("#assistantForm");
const input = document.querySelector("#assistantInput");
const sendButton = document.querySelector("#sendButton");
const stopButton = document.querySelector("#stopButton");
const messages = document.querySelector("#messages");
const status = document.querySelector("#assistantStatus");
const contextPanel = document.querySelector(".context-panel");
const drawerScrim = document.querySelector("#drawerScrim");
const sessionPanel = document.querySelector("#sessionPanel");
const sessionList = document.querySelector("#sessionList");
const sessionEmpty = document.querySelector("#sessionEmpty");
const longConversationList = document.querySelector("#longConversationList");
const longConversationEmpty = document.querySelector("#longConversationEmpty");
const longConversationPanel = document.querySelector("#longConversationPanel");
const newSessionButton = document.querySelector("#newSessionButton");
const guestMemoryNotice = document.querySelector("#guestMemoryNotice");
const clearGuestHistoryButton = document.querySelector("#clearGuestHistoryButton");
const closeSessionsButton = document.querySelector("#closeSessionsButton");
const mobileSessionsButton = document.querySelector("#mobileSessionsButton");
const sessionRenameDialog = document.querySelector("#sessionRenameDialog");
const sessionRenameForm = document.querySelector("#sessionRenameForm");
const sessionRenameInput = document.querySelector("#sessionRenameInput");
const sessionRenameState = document.querySelector("#sessionRenameState");
const sessionRenameCancel = document.querySelector("#sessionRenameCancel");
const welcomeTemplate = document.querySelector("#welcome")?.cloneNode(true);
let activeController = null;
let streamAvailable;
let sessionAvailable = false;
let currentSessionId = null;
let capabilitiesPromise = null;
let sessionCreationBlocked = false;
let renamingSession = null;
const sessionEpoch = new AssistantSessionEpoch(getAccessToken());
let authenticatedMode = Boolean(getAccessToken());
let assistantModeInitialized = false;
let sessionListRequestVersion = { short: 0, long: 0 };

function isAuthenticatedMode() {
  return authenticatedMode;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function safeSiteHref(href) {
  try {
    const url = new URL(href, window.location.href);
    return url.origin === window.location.origin ? `${url.pathname.split("/").pop()}${url.search}${url.hash}` : null;
  } catch {
    return null;
  }
}

function addMessage(role, text, error = false) {
  document.querySelector("#welcome")?.remove();
  const article = element("article", `message ${role}`);
  article.appendChild(element("div", "message-label", role === "user" ? "你" : "助手"));
  const body = element("div", `message-body${error ? " error-line" : ""}`, text);
  article.appendChild(body);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return body;
}

function requestId(prefix = "request") {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return `${prefix}-${globalThis.crypto.randomUUID()}`;
  }
  // HTTP test browsers may not expose randomUUID. This identifier is only
  // an idempotency key, never an authentication or authorization secret.
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

function canOfferRetry(error, answerBody) {
  if (answerBody) return true;
  if ([502, 503, 504].includes(error?.status)) return true;
  return [
    "API_NETWORK_ERROR",
    "API_OFFLINE",
    "API_TIMEOUT",
    "API_STREAM_BODY_MISSING",
  ].includes(error?.code);
}

function renderRetry(answerBody, retryContext) {
  const body = answerBody || addMessage(
    "assistant",
    "连接中断，本次回答可能未完成。",
    true,
  );
  body.textContent = "连接中断，本次回答可能未完成。";
  body.classList.add("error-line");
  const article = body.closest(".message");
  const action = element("div", "message-retry");
  action.appendChild(element(
    "p",
    "",
    "仅在你确认后重试；若服务端已完成，将复用同一结果。",
  ));
  const button = element("button", "", "重新发送");
  button.type = "button";
  button.dataset.agentRetry = "true";
  button.addEventListener("click", () => {
    article?.remove();
    submitMessage(retryContext.message, {
      requestId: retryContext.requestId,
      sessionId: retryContext.sessionId,
      retry: true,
    });
  });
  action.appendChild(button);
  article?.appendChild(action);
}

function resetConversation() {
  messages.replaceChildren();
  if (welcomeTemplate) messages.appendChild(welcomeTemplate.cloneNode(true));
}

function setCurrentSession(sessionId) {
  currentSessionId = sessionId || null;
  sessionPanel?.querySelectorAll("[data-session-id]").forEach((button) => {
    button.classList.toggle("active", button.dataset.sessionId === currentSessionId);
    button.setAttribute(
      "aria-current",
      button.dataset.sessionId === currentSessionId ? "true" : "false",
    );
  });
}

function syncNewSessionButton() {
  if (!newSessionButton) return;
  newSessionButton.disabled = sessionCreationBlocked || Boolean(activeController);
  newSessionButton.title = sessionCreationBlocked
    ? "请先在当前对话中完成一次问答"
    : "";
}

function closeMobileSessions({ restoreFocus = false } = {}) {
  const wasOpen = contextPanel?.classList.contains("session-drawer-open");
  contextPanel?.classList.remove("session-drawer-open");
  if (drawerScrim) drawerScrim.hidden = true;
  mobileSessionsButton?.setAttribute("aria-expanded", "false");
  if (restoreFocus && wasOpen) mobileSessionsButton?.focus();
}

function openMobileSessions() {
  contextPanel?.classList.add("session-drawer-open");
  if (drawerScrim) drawerScrim.hidden = false;
  mobileSessionsButton?.setAttribute("aria-expanded", "true");
  closeSessionsButton?.focus();
}

function stopActiveRequest() {
  activeController?.abort(new DOMException("用户停止生成", "AbortError"));
}

function sessionDate(value) {
  const normalized = String(value || "").replace(" ", "T");
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(normalized);
  const date = new Date(hasTimezone ? normalized : `${normalized}Z`);
  return Number.isNaN(date.getTime())
    ? ""
    : new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
}

function conversationEndpoint(sessionId) {
  return sessionId?.startsWith("agl_")
    ? `/agent/long-conversations/${sessionId}`
    : `/agent/sessions/${sessionId}`;
}

function renderConversationList(container, items = [], type = "short") {
  const fragment = document.createDocumentFragment();
  items.forEach((session) => {
    const sessionId = type === "long" ? session.conversationId : session.sessionId;
    const row = element("div", "session-row");
    const open = element("button", "session-open");
    open.type = "button";
    open.dataset.sessionId = sessionId;
    const titleLine = element("span", "session-title-line");
    titleLine.appendChild(element("strong", "", session.title));
    if (session.pinned) titleLine.appendChild(element("span", "session-pin-badge", "置顶"));
    open.append(
      titleLine,
      element("span", "", `${session.messageCount} 条 · ${sessionDate(session.updatedAt)}`),
    );

    const actions = document.createElement("details");
    actions.className = "session-actions";
    const summary = document.createElement("summary");
    summary.setAttribute("aria-label", `管理会话：${session.title}`);
    summary.textContent = "•••";
    const menu = element("div", "session-actions-menu");
    menu.setAttribute("role", "menu");
    const pin = element("button", "", session.pinned ? "取消置顶" : "置顶");
    pin.type = "button";
    pin.dataset.pinSessionId = sessionId;
    pin.dataset.pinned = session.pinned ? "true" : "false";
    const rename = element("button", "", "修改标题");
    rename.type = "button";
    rename.dataset.renameSessionId = sessionId;
    rename.dataset.sessionTitle = session.title;
    menu.append(pin, rename);
    if (type === "short") {
      const upgrade = element("button", "", "升级为长期对话");
      upgrade.type = "button";
      upgrade.dataset.upgradeSessionId = sessionId;
      upgrade.disabled = Number(session.messageCount) === 0;
      if (upgrade.disabled) upgrade.title = "完成一次问答后才能升级";
      menu.appendChild(upgrade);
    }
    const remove = element("button", "session-delete", "删除");
    remove.type = "button";
    remove.dataset.deleteSessionId = sessionId;
    remove.setAttribute("aria-label", `删除会话：${session.title}`);
    menu.appendChild(remove);
    actions.append(summary, menu);
    row.append(open, actions);
    fragment.appendChild(row);
  });
  container.replaceChildren(fragment);
}

function renderSessionList(items = []) {
  sessionCreationBlocked = items.some((session) => Number(session.messageCount) === 0);
  renderConversationList(sessionList, items, "short");
  sessionEmpty.hidden = items.length > 0;
  setCurrentSession(currentSessionId);
  syncNewSessionButton();
}

function renderLongConversationList(items = []) {
  renderConversationList(longConversationList, items, "long");
  longConversationEmpty.hidden = items.length > 0;
  setCurrentSession(currentSessionId);
}

function renderGuestSessionList(items = []) {
  const fragment = document.createDocumentFragment();
  items.forEach((conversation) => {
    const row = element("div", "session-row");
    const open = element("button", "session-open");
    open.type = "button";
    open.dataset.sessionId = conversation.id;
    open.append(
      element("strong", "", conversation.title),
      element("span", "", `${conversation.messages.length} 条 · 浏览器内`),
    );
    row.appendChild(open);
    fragment.appendChild(row);
  });
  sessionList.replaceChildren(fragment);
  sessionEmpty.hidden = items.length > 0;
  sessionEmpty.textContent = "还没有浏览器游客对话";
  setCurrentSession(currentSessionId);
}

function renderGuestConversation(conversationId = currentSessionId) {
  const conversations = loadGuestConversations();
  const conversation = conversations.find((item) => item.id === conversationId)
    || conversations[0]
    || null;
  renderGuestSessionList(conversations);
  if (!conversation) {
    setCurrentSession(null);
    resetConversation();
    status.textContent = "游客模式 · 浏览器内保存";
    return;
  }
  messages.replaceChildren();
  conversation.messages.forEach((message) => addMessage(message.role, message.content));
  setCurrentSession(conversation.id);
  status.textContent = "游客模式 · 浏览器内保存";
}

async function loadSessionList({ short = true, long = true } = {}) {
  if (!isAuthenticatedMode() || !sessionAvailable) return;
  const requestVersion = {
    short: short ? ++sessionListRequestVersion.short : null,
    long: long ? ++sessionListRequestVersion.long : null,
  };
  const operation = sessionEpoch.beginOperation();
  try {
    const [shortResult, longResult] = await Promise.allSettled([
      short ? apiGet(
        "/agent/sessions",
        { limit: 20, offset: 0 },
        { retryCount: 0, signal: operation.signal },
      ) : Promise.resolve(null),
      long ? apiGet(
        "/agent/long-conversations",
        { limit: 20, offset: 0 },
        { retryCount: 0, signal: operation.signal },
      ) : Promise.resolve(null),
    ]);
    if (!operation.isCurrent()) return;
    const shortCurrent = short && requestVersion.short === sessionListRequestVersion.short;
    const longCurrent = long && requestVersion.long === sessionListRequestVersion.long;
    const unauthorized = [shortResult, longResult].some(
      (result) => result.status === "rejected" && result.reason?.status === 401,
    );
    if (unauthorized) {
      sessionPanel.hidden = true;
      return;
    }
    if (shortCurrent) {
      if (shortResult.status === "fulfilled") {
        renderSessionList(shortResult.value?.items || []);
      } else {
        sessionEmpty.hidden = false;
        sessionEmpty.textContent = "会话列表暂时不可用";
        sessionCreationBlocked = true;
        syncNewSessionButton();
      }
    }
    if (longCurrent) {
      if (longResult.status === "fulfilled") {
        renderLongConversationList(longResult.value?.items || []);
      } else {
        longConversationEmpty.hidden = false;
        longConversationEmpty.textContent = "长期对话暂时不可用";
      }
    }
  } catch (error) {
    if (!operation.isCurrent()) return;
    const shortCurrent = short && requestVersion.short === sessionListRequestVersion.short;
    const longCurrent = long && requestVersion.long === sessionListRequestVersion.long;
    if (!shortCurrent && !longCurrent) return;
    if (shortCurrent) {
      sessionEmpty.hidden = false;
      sessionEmpty.textContent = "会话列表暂时不可用";
      sessionCreationBlocked = true;
      syncNewSessionButton();
    }
    if (longCurrent) {
      longConversationEmpty.hidden = false;
      longConversationEmpty.textContent = "长期对话暂时不可用";
    }
  } finally {
    operation.finish();
  }
}

async function createSession() {
  if (!isAuthenticatedMode()) {
    if (activeController) return;
    const conversation = createGuestConversation("新对话");
    renderGuestConversation(conversation.id);
    closeMobileSessions();
    input.focus();
    return;
  }
  if (!sessionAvailable || activeController) return;
  if (sessionCreationBlocked) {
    status.textContent = "请先完成当前对话";
    return;
  }
  const operation = sessionEpoch.beginOperation();
  newSessionButton.disabled = true;
  try {
    const result = await apiPost("/agent/sessions", {}, { signal: operation.signal });
    if (!operation.isCurrent()) return;
    resetConversation();
    setCurrentSession(result.session.sessionId);
    status.textContent = "短期会话已开启";
    await loadSessionList();
    if (!operation.isCurrent()) return;
    closeMobileSessions();
    input.focus();
  } catch (error) {
    if (!operation.isCurrent()) return;
    if (error?.code === "AGENT_SESSION_UNSTARTED_EXISTS") {
      status.textContent = "请先完成当前对话";
      await loadSessionList();
      if (!operation.isCurrent()) return;
    } else {
      addMessage("assistant", error.message || "无法创建短期会话。", true);
    }
  } finally {
    const current = operation.isCurrent();
    operation.finish();
    if (current) syncNewSessionButton();
  }
}

async function restoreSession(sessionId) {
  if (!sessionId || activeController) return;
  if (!isAuthenticatedMode()) {
    renderGuestConversation(sessionId);
    closeMobileSessions();
    input.focus();
    return;
  }
  const operation = sessionEpoch.beginOperation();
  status.textContent = "载入会话";
  try {
    const isLong = sessionId.startsWith("agl_");
    const result = await apiGet(conversationEndpoint(sessionId), {
      messageLimit: 100,
      messageOffset: 0,
    }, { retryCount: 0, signal: operation.signal });
    if (!operation.isCurrent()) return;
    messages.replaceChildren();
    (result.messages || []).forEach((message) => addMessage(message.role, message.content));
    if (!result.messages?.length) resetConversation();
    setCurrentSession(sessionId);
    status.textContent = isLong ? "长期对话" : "短期会话";
    closeMobileSessions();
    input.focus();
  } catch (error) {
    if (!operation.isCurrent()) return;
    if (
      error?.code === "AGENT_SESSION_NOT_FOUND"
      || error?.code === "AGENT_LONG_CONVERSATION_NOT_FOUND"
    ) {
      setCurrentSession(null);
      await loadSessionList();
      if (!operation.isCurrent()) return;
    }
    addMessage("assistant", error.message || "无法载入短期会话。", true);
    status.textContent = "载入失败";
  } finally {
    operation.finish();
  }
}

async function deleteSession(button) {
  if (!isAuthenticatedMode()) return;
  const sessionId = button.dataset.deleteSessionId;
  if (!sessionId || activeController) return;
  if (button.dataset.confirmDelete !== "true") {
    button.dataset.confirmDelete = "true";
    button.textContent = "确认";
    globalThis.setTimeout(() => {
      if (button.isConnected) {
        delete button.dataset.confirmDelete;
        button.textContent = "删除";
      }
    }, 4000);
    return;
  }
  const operation = sessionEpoch.beginOperation();
  button.disabled = true;
  try {
    await apiDelete(conversationEndpoint(sessionId), { signal: operation.signal });
    if (!operation.isCurrent()) return;
    if (currentSessionId === sessionId) {
      setCurrentSession(null);
      resetConversation();
      status.textContent = "会话已删除";
    }
    await loadSessionList();
    if (!operation.isCurrent()) return;
  } catch (error) {
    if (!operation.isCurrent()) return;
    button.disabled = false;
    button.textContent = "重试";
    addMessage("assistant", error.message || "删除会话失败。", true);
  } finally {
    operation.finish();
  }
}

function openRenameSession(button) {
  if (!sessionRenameDialog || !sessionRenameInput) return;
  renamingSession = {
    sessionId: button.dataset.renameSessionId,
    title: button.dataset.sessionTitle || "",
  };
  sessionRenameInput.value = renamingSession.title;
  sessionRenameState.textContent = "";
  sessionRenameDialog.showModal();
  sessionRenameInput.focus();
  sessionRenameInput.select();
}

async function togglePinnedSession(button) {
  if (!isAuthenticatedMode()) return;
  const sessionId = button.dataset.pinSessionId;
  if (!sessionId || activeController) return;
  const operation = sessionEpoch.beginOperation();
  button.disabled = true;
  try {
    await apiPatch(conversationEndpoint(sessionId), {
      pinned: button.dataset.pinned !== "true",
    }, { signal: operation.signal });
    if (!operation.isCurrent()) return;
    await loadSessionList();
    if (!operation.isCurrent()) return;
  } catch (error) {
    if (!operation.isCurrent()) return;
    addMessage("assistant", error.message || "无法更新会话置顶状态。", true);
  } finally {
    const current = operation.isCurrent();
    operation.finish();
    if (current) button.disabled = false;
  }
}

async function upgradeSession(button) {
  if (!isAuthenticatedMode()) return;
  const sessionId = button.dataset.upgradeSessionId;
  if (!sessionId || activeController) return;
  const operation = sessionEpoch.beginOperation();
  button.disabled = true;
  try {
    const result = await apiPost(
      `/agent/sessions/${sessionId}/upgrade`,
      {},
      { signal: operation.signal },
    );
    if (!operation.isCurrent()) return;
    if (currentSessionId === sessionId) {
      setCurrentSession(result.conversation.conversationId);
      status.textContent = "已升级为长期对话";
    }
    await loadSessionList();
    if (!operation.isCurrent()) return;
  } catch (error) {
    if (!operation.isCurrent()) return;
    if (error?.code === "AGENT_LONG_CONVERSATION_LIMIT_REACHED") {
      status.textContent = "最多保存三个长期对话";
    } else {
      addMessage("assistant", error.message || "无法升级为长期对话。", true);
    }
  } finally {
    const current = operation.isCurrent();
    operation.finish();
    if (current) button.disabled = false;
  }
}

function renderCards(cards = []) {
  if (!cards.length) return;
  const section = element("section", "response-section");
  section.appendChild(element("h3", "", "相关入口"));
  const list = element("div", "result-list");
  cards.forEach((card) => {
    const href = safeSiteHref(card.href);
    if (!href) return;
    const link = element("a", "result-card");
    link.href = href;
    const content = element("div");
    content.appendChild(element("strong", "", card.title));
    content.appendChild(element("p", "", card.description || card.reason || "站内来源"));
    link.append(content, element("span", "result-arrow", "›"));
    list.appendChild(link);
  });
  section.appendChild(list);
  messages.appendChild(section);
}

function renderSteps(steps = [], draft = null) {
  if (!steps.length) return;
  const section = element("section", "response-section");
  section.appendChild(element("h3", "", draft ? "工作流草案" : "建议顺序"));
  const list = element("div", "step-list");
  steps.forEach((step) => {
    const row = element("div", "step-row");
    const content = element("div");
    content.appendChild(element("strong", "", `${step.order}. ${step.name}`));
    content.appendChild(element("p", "", step.objective));
    row.appendChild(content);
    const href = safeSiteHref(step.targetHref);
    if (href) {
      const link = element("a", "result-arrow", "›");
      link.href = href;
      link.setAttribute("aria-label", `打开 ${step.name}`);
      row.appendChild(link);
    }
    list.appendChild(row);
  });
  section.appendChild(list);
  if (draft) section.appendChild(buildSaveControl(draft));
  messages.appendChild(section);
}

function buildSaveControl(draft) {
  const guestDraft = !isAuthenticatedMode();
  const box = element("div", "save-workflow");
  const heading = element("div", "save-workflow-heading");
  heading.append(
    element("strong", "", "保存前检查草稿"),
    element(
      "p",
      "",
      guestDraft
        ? "游客可在本页创建和编辑草稿，但不能保存或归档；登录不会自动导入这份草稿。"
        : "你可以修改标题、说明和步骤。只有确认后才会写入个人工作流。",
    ),
  );

  const editor = element("div", "workflow-draft-editor");
  const titleLabel = element("label", "workflow-draft-field");
  titleLabel.appendChild(element("span", "", "标题"));
  const titleInput = document.createElement("input");
  titleInput.type = "text";
  titleInput.maxLength = 120;
  titleInput.required = true;
  titleInput.value = draft.title || "";
  titleLabel.appendChild(titleInput);

  const descriptionLabel = element("label", "workflow-draft-field");
  descriptionLabel.appendChild(element("span", "", "说明"));
  const descriptionInput = document.createElement("textarea");
  descriptionInput.rows = 2;
  descriptionInput.maxLength = 600;
  descriptionInput.value = draft.description || "";
  descriptionLabel.appendChild(descriptionInput);
  editor.append(titleLabel, descriptionLabel);

  const stepEditors = (draft.steps || []).map((step) => {
    const stepBox = element("fieldset", "workflow-draft-step");
    const legend = element("legend", "", `步骤 ${step.order}`);
    const nameLabel = element("label", "workflow-draft-field");
    nameLabel.appendChild(element("span", "", "名称"));
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.maxLength = 100;
    nameInput.required = true;
    nameInput.value = step.name || "";
    nameLabel.appendChild(nameInput);
    const objectiveLabel = element("label", "workflow-draft-field");
    objectiveLabel.appendChild(element("span", "", "目标"));
    const objectiveInput = document.createElement("textarea");
    objectiveInput.rows = 2;
    objectiveInput.maxLength = 500;
    objectiveInput.required = true;
    objectiveInput.value = step.objective || "";
    objectiveLabel.appendChild(objectiveInput);
    stepBox.append(legend, nameLabel, objectiveLabel);
    if (step.toolSlug) {
      stepBox.appendChild(element("p", "workflow-draft-tool", `工具：${step.toolSlug}`));
    }
    editor.appendChild(stepBox);
    return { step, nameInput, objectiveInput };
  });

  const confirmation = element("label", "workflow-save-confirmation");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  confirmation.append(
    checkbox,
    document.createTextNode("我已检查以上内容，确认保存到个人工作流资产。"),
  );

  const state = element("p", "workflow-save-state", "尚未写入");
  state.setAttribute("aria-live", "polite");
  const destination = element("a", "workflow-save-link", "查看个人工作流");
  destination.href = safeInternalHref("/settings#workflows");
  destination.hidden = true;
  const button = element("button", "", "保存工作流");
  button.type = "button";
  button.disabled = true;
  if (guestDraft) button.title = "登录后重新生成并确认草稿，才能保存到个人工作流";
  let stableKey = requestId("agent");
  let submittedPayload = null;

  const setEditorDisabled = (disabled) => {
    [titleInput, descriptionInput, ...stepEditors.flatMap((item) => [
      item.nameInput,
      item.objectiveInput,
    ])].forEach((control) => { control.disabled = disabled; });
  };

  const currentPayload = () => ({
    ...draft,
    title: titleInput.value.trim(),
    description: descriptionInput.value.trim() || null,
    confirmed: true,
    steps: stepEditors.map(({ step, nameInput, objectiveInput }) => ({
      ...step,
      name: nameInput.value.trim(),
      objective: objectiveInput.value.trim(),
    })),
  });

  checkbox.addEventListener("change", () => {
    button.disabled = guestDraft || !checkbox.checked;
  });
  button.addEventListener("click", async () => {
    if (!isAuthenticatedMode()) {
      state.textContent = "游客草稿仅保留在本页，不能保存或归档。";
      state.classList.add("error-line");
      return;
    }
    if (!submittedPayload) {
      const candidate = currentPayload();
      if (
        !candidate.title
        || !candidate.steps.length
        || candidate.steps.some((step) => !step.name || !step.objective)
      ) {
        state.textContent = "请补全标题、步骤名称和目标。";
        state.classList.add("error-line");
        return;
      }
      submittedPayload = candidate;
      setEditorDisabled(true);
      checkbox.disabled = true;
    }
    button.disabled = true;
    button.textContent = "保存中";
    state.textContent = "正在执行同一次保存命令…";
    state.classList.remove("error-line");
    try {
      const result = await saveAgentWorkflow(submittedPayload, stableKey);
      button.textContent = result.meta?.idempotencyReplayed ? "已确认保存" : "已保存";
      state.textContent = result.meta?.idempotencyReplayed
        ? "已复用先前完成的同一次保存，没有创建重复工作流。"
        : "已保存到个人工作流。";
      const workflowUid = result.workflow?.workflowUid;
      destination.href = workflowUid
        ? safeInternalHref(`/settings?workflow=${encodeURIComponent(workflowUid)}#workflows`)
        : safeInternalHref("/settings#workflows");
      destination.textContent = "查看已保存的工作流";
      destination.hidden = false;
      button.disabled = true;
    } catch (error) {
      button.textContent = "重试同一次保存";
      button.disabled = false;
      state.textContent = error?.code === "WORKFLOW_IDEMPOTENCY_CONFLICT"
        ? "保存标识与另一份草稿冲突。请刷新页面后检查个人工作流。"
        : "保存结果尚未确认；重试会复用同一保存标识，不会主动创建新请求。";
      state.classList.add("error-line");
      destination.href = safeInternalHref("/settings#workflows");
      destination.textContent = "核对个人工作流";
      destination.hidden = false;
    }
  });
  box.append(heading, editor, confirmation, state, button, destination);
  return box;
}

function renderEvidence(response) {
  const section = element("section", "response-section evidence-inline");
  const evidenceList = element("div", "evidence-list");
  const toolCalls = element("div", "tool-calls");
  (response.citations || []).forEach((citation) => {
    const href = safeSiteHref(citation.href);
    if (!href) return;
    const link = element("a", "evidence-item");
    link.href = href;
    link.append(
      element("span", "evidence-type", citation.sourceType === "tool" ? "工具" : "学习节点"),
      element("strong", "", citation.title),
    );
    evidenceList.appendChild(link);
  });
  (response.toolCalls || []).forEach((call) => {
    const row = element("div", "tool-call");
    row.append(element("span", "", call.name), element("strong", "", call.status === "skipped" ? "跳过" : String(call.resultCount)));
    toolCalls.appendChild(row);
  });
  if (!evidenceList.children.length && !toolCalls.children.length) return;
  section.appendChild(element("h3", "", "来源"));
  if (evidenceList.children.length) section.appendChild(evidenceList);
  if (toolCalls.children.length) section.appendChild(toolCalls);
  messages.appendChild(section);
}

function renderResponse(response, answerBody = null) {
  if (answerBody) answerBody.textContent = response.answer;
  else addMessage("assistant", response.answer);
  renderCards(response.cards);
  renderSteps(response.workflowSteps, response.workflowDraft);
  renderEvidence(response);
  if (response.meta?.mode === "provider") {
    status.textContent = "模型回答 · 只读";
  } else if (response.meta?.fallbackReason) {
    status.textContent = "确定性回退 · 只读";
  } else {
    status.textContent = response.meta?.readOnly ? "只读结果" : "已完成";
  }
}

async function capabilities(signal) {
  if (capabilitiesPromise) return capabilitiesPromise;
  try {
    const result = await apiGet("/agent/capabilities", {}, { retryCount: 0, signal });
    if (signal?.aborted) throw signal.reason || new DOMException("Aborted", "AbortError");
    capabilitiesPromise = Promise.resolve(result);
    return result;
  } catch (error) {
    if (signal?.aborted || error?.code === "API_REQUEST_ABORTED") throw error;
    const fallback = { stream: false, sessions: false, transportVersion: 1 };
    capabilitiesPromise = Promise.resolve(fallback);
    return fallback;
  }
}

async function canUseStream(signal) {
  if (typeof streamAvailable === "boolean") return streamAvailable;
  const available = await capabilities(signal);
  streamAvailable = available.stream === true && available.transportVersion === 1;
  return streamAvailable;
}

async function initializeSessions() {
  if (!isAuthenticatedMode()) return;
  const operation = sessionEpoch.beginOperation();
  try {
    const available = await capabilities(operation.signal);
    if (!operation.isCurrent()) return;
    sessionAvailable = available.sessions === true && available.transportVersion === 1;
    sessionPanel.hidden = !sessionAvailable;
    newSessionButton.hidden = !sessionAvailable;
    mobileSessionsButton.hidden = !sessionAvailable;
    if (sessionAvailable) {
      await loadSessionList();
      if (!operation.isCurrent()) return;
    }
  } catch (error) {
    if (operation.isCurrent()) throw error;
  } finally {
    operation.finish();
  }
}

async function initializeAssistantMode() {
  const token = getAccessToken();
  const identityChanged = sessionEpoch.transition(token);
  const nextAuthenticatedMode = Boolean(token);
  if (!identityChanged && assistantModeInitialized) return;
  if (identityChanged && activeController) {
    stopActiveRequest();
    activeController = null;
    sendButton.disabled = false;
    stopButton.hidden = true;
  }
  authenticatedMode = nextAuthenticatedMode;
  assistantModeInitialized = true;
  renamingSession = null;
  if (sessionRenameDialog?.open) sessionRenameDialog.close();
  setCurrentSession(null);
  resetConversation();
  closeMobileSessions();
  if (guestMemoryNotice) guestMemoryNotice.hidden = authenticatedMode;
  if (longConversationPanel) longConversationPanel.hidden = !authenticatedMode;

  if (!authenticatedMode) {
    sessionAvailable = false;
    sessionCreationBlocked = false;
    sessionPanel.hidden = false;
    newSessionButton.hidden = false;
    mobileSessionsButton.hidden = false;
    renderGuestConversation();
    syncNewSessionButton();
    return;
  }

  sessionPanel.hidden = true;
  newSessionButton.hidden = true;
  mobileSessionsButton.hidden = true;
  await initializeSessions();
}

async function requestStream(payload, controller, stableRequestId, operation) {
  let answerBody = null;
  let completedResponse = null;
  let started = false;
  let answerBuffer = null;
  try {
    const response = await apiPostStream("/agent/chat/stream", payload, {
      signal: controller.signal,
      headers: { "X-Request-Id": stableRequestId },
    });
    if (!operation.isCurrent()) throw operation.signal.reason;
    await consumeAgentEventStream(response, async (event) => {
      if (!operation.isCurrent()) return;
      if (event.event === "response.started") {
        started = true;
        answerBody = addMessage("assistant", "");
        answerBuffer = createFrameBuffer((chunk) => {
          answerBody.textContent += chunk;
          messages.scrollTop = messages.scrollHeight;
        });
        status.textContent = "生成中";
      } else if (event.event === "response.answer.delta") {
        answerBuffer.push(event.delta);
      } else if (event.event === "response.completed") {
        completedResponse = event.response;
      }
    }, { signal: controller.signal });
    if (!operation.isCurrent()) throw operation.signal.reason;
    if (!completedResponse) throw new Error("流式回答缺少完成事件");
    return { response: completedResponse, answerBody };
  } catch (error) {
    if (!operation.isCurrent()) throw operation.signal.reason || error;
    const canFallback = !started && (
      [404, 405, 503].includes(error.status)
      || ["AGENT_STREAM_DISABLED", "API_STREAM_CONTENT_TYPE_INVALID"].includes(error.code)
    );
    if (!canFallback) {
      error.answerBody = answerBody;
      throw error;
    }
    streamAvailable = false;
    const response = await apiPost("/agent/chat", payload, {
      signal: controller.signal,
      headers: { "X-Request-Id": stableRequestId },
    });
    if (!operation.isCurrent()) throw operation.signal.reason;
    return { response, answerBody: null };
  } finally {
    answerBuffer?.flush();
  }
}

async function submitMessage(message, options = {}) {
  const text = String(message || "").trim();
  if (!text || activeController) return;
  const authenticatedRequest = isAuthenticatedMode();
  const stableRequestId = options.requestId || requestId();
  let requestSessionId = options.sessionId ?? currentSessionId;
  if (!authenticatedRequest && !requestSessionId) {
    const conversation = createGuestConversation(text.slice(0, 40));
    requestSessionId = conversation.id;
    setCurrentSession(requestSessionId);
    renderGuestSessionList(loadGuestConversations());
  }
  if (!options.retry) {
    addMessage("user", text);
    input.value = "";
  }
  const operation = sessionEpoch.beginOperation();
  const controller = new AbortController();
  activeController = controller;
  sendButton.disabled = true;
  stopButton.hidden = false;
  status.textContent = "检索中";
  syncNewSessionButton();
  let answerBody = null;
  try {
    const payload = {
      message: text,
      pageContext: { page: "assistant", url: window.location.pathname },
    };
    if (authenticatedRequest && requestSessionId) payload.sessionId = requestSessionId;
    let response;
    if (!authenticatedRequest) {
      payload.history = recentGuestHistory(requestSessionId);
      response = await apiPost("/agent/guest/chat", payload, {
        signal: controller.signal,
        headers: { "X-Request-Id": stableRequestId },
      });
      if (!operation.isCurrent()) return;
    } else {
      const useStream = await canUseStream(controller.signal);
      if (!operation.isCurrent()) return;
      if (useStream) {
        const streamed = await requestStream(
          payload,
          controller,
          stableRequestId,
          operation,
        );
        if (!operation.isCurrent()) return;
        response = streamed.response;
        answerBody = streamed.answerBody;
      } else {
        response = await apiPost("/agent/chat", payload, {
          signal: controller.signal,
          headers: { "X-Request-Id": stableRequestId },
        });
        if (!operation.isCurrent()) return;
      }
    }
    if (!authenticatedRequest) {
      appendGuestMessage(requestSessionId, "user", text);
      appendGuestMessage(requestSessionId, "assistant", response.answer);
    }
    renderResponse(response, answerBody);
    if (authenticatedRequest && currentSessionId) {
      void loadSessionList({
        short: !currentSessionId.startsWith("agl_"),
        long: currentSessionId.startsWith("agl_"),
      });
    } else if (!authenticatedRequest) {
      renderGuestSessionList(loadGuestConversations());
    }
  } catch (error) {
    if (!operation.isCurrent()) return;
    answerBody ||= error?.answerBody || null;
    if (controller.signal.aborted || error?.code === "API_REQUEST_ABORTED") {
      if (answerBody) answerBody.textContent = "已停止生成。";
      else addMessage("assistant", "已停止生成。");
      status.textContent = "已停止";
    } else if (error instanceof ApiError && error.status === 401) {
      addMessage("assistant", "请先登录后使用站内助手。登录完成后可以重新发送刚才的问题。", true);
      document.querySelector('[data-auth-trigger="login"]')?.click();
      status.textContent = "需要登录";
    } else if (canOfferRetry(error, answerBody)) {
      if (!authenticatedRequest) input.value = text;
      renderRetry(answerBody, {
        message: text,
        requestId: stableRequestId,
        sessionId: requestSessionId,
      });
      status.textContent = "连接中断";
    } else {
      if (!authenticatedRequest) input.value = text;
      addMessage("assistant", error.message || "助手暂时不可用，请稍后重试。", true);
      status.textContent = "请求失败";
    }
  } finally {
    const current = operation.isCurrent();
    operation.finish();
    if (activeController === controller) activeController = null;
    if (current) {
      sendButton.disabled = false;
      stopButton.hidden = true;
      syncNewSessionButton();
      input.focus();
    }
  }
}

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMessage(input.value);
});
input?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
stopButton?.addEventListener("click", stopActiveRequest);
newSessionButton?.addEventListener("click", createSession);
closeSessionsButton?.addEventListener("click", () => closeMobileSessions({ restoreFocus: true }));
drawerScrim?.addEventListener("click", () => closeMobileSessions({ restoreFocus: true }));
mobileSessionsButton?.addEventListener("click", () => {
  const open = !contextPanel?.classList.contains("session-drawer-open");
  if (open) openMobileSessions();
  else closeMobileSessions({ restoreFocus: true });
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (contextPanel?.classList.contains("session-drawer-open")) {
    event.preventDefault();
    closeMobileSessions({ restoreFocus: true });
    return;
  }
  if (activeController) {
    event.preventDefault();
    stopActiveRequest();
  }
});
sessionPanel?.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-session-id]");
  if (deleteButton) {
    deleteSession(deleteButton);
    return;
  }
  const pinButton = event.target.closest("[data-pin-session-id]");
  if (pinButton) {
    togglePinnedSession(pinButton);
    return;
  }
  const renameButton = event.target.closest("[data-rename-session-id]");
  if (renameButton) {
    openRenameSession(renameButton);
    return;
  }
  const upgradeButton = event.target.closest("[data-upgrade-session-id]");
  if (upgradeButton) {
    upgradeSession(upgradeButton);
    return;
  }
  const openButton = event.target.closest("[data-session-id]");
  if (openButton) restoreSession(openButton.dataset.sessionId);
});

sessionRenameCancel?.addEventListener("click", () => {
  sessionRenameDialog?.close();
});
sessionRenameForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!isAuthenticatedMode()) {
    sessionRenameDialog?.close();
    return;
  }
  const title = sessionRenameInput?.value.trim() || "";
  if (!renamingSession?.sessionId || !title) {
    sessionRenameState.textContent = "标题不能为空";
    return;
  }
  const submit = sessionRenameForm.querySelector('button[type="submit"]');
  const sessionId = renamingSession.sessionId;
  const operation = sessionEpoch.beginOperation();
  submit.disabled = true;
  sessionRenameState.textContent = "保存中";
  try {
    await apiPatch(
      conversationEndpoint(sessionId),
      { title },
      { signal: operation.signal },
    );
    if (!operation.isCurrent()) return;
    sessionRenameDialog.close();
    await loadSessionList();
    if (!operation.isCurrent()) return;
  } catch (error) {
    if (!operation.isCurrent()) return;
    sessionRenameState.textContent = error.message || "标题保存失败";
  } finally {
    const current = operation.isCurrent();
    operation.finish();
    if (current) submit.disabled = false;
  }
});
document.addEventListener("click", (event) => {
  const settingsLink = event.target.closest("[data-settings-link]");
  if (!settingsLink || isAuthenticatedMode()) return;
  event.preventDefault();
  status.textContent = "请先登录后进入设置";
  document.querySelector('[data-auth-trigger="login"]')?.click();
});
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (button) submitMessage(button.dataset.prompt);
});
clearGuestHistoryButton?.addEventListener("click", () => {
  if (isAuthenticatedMode()) return;
  if (!window.confirm("确定清除当前浏览器中的全部游客对话吗？此操作无法撤销。")) return;
  clearGuestConversations();
  renderGuestConversation(null);
  status.textContent = "游客记录已清除";
});
window.addEventListener("ai-nav-auth-changed", () => {
  void initializeAssistantMode();
});
void initializeAssistantMode();
