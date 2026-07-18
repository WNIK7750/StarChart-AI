import { ApiError, apiPost } from "./api.js";
import { saveAgentWorkflow } from "./users-api.js";

const form = document.querySelector("#assistantForm");
const input = document.querySelector("#assistantInput");
const sendButton = document.querySelector("#sendButton");
const messages = document.querySelector("#messages");
const status = document.querySelector("#assistantStatus");
const evidenceEmpty = document.querySelector("#evidenceEmpty");
const evidenceList = document.querySelector("#evidenceList");
const toolCalls = document.querySelector("#toolCalls");
const assetSummary = document.querySelector("#assetSummary");

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
  const box = element("div", "save-workflow");
  const label = element("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  label.append(checkbox, document.createTextNode("我确认将这份草案保存到个人工作流资产。"));
  const button = element("button", "", "保存工作流");
  button.type = "button";
  button.disabled = true;
  checkbox.addEventListener("change", () => { button.disabled = !checkbox.checked; });
  button.addEventListener("click", async () => {
    button.disabled = true;
    button.textContent = "保存中";
    try {
      const key = `agent-${crypto.randomUUID()}`;
      await saveAgentWorkflow({ ...draft, confirmed: true }, key);
      button.textContent = "已保存";
      checkbox.disabled = true;
    } catch (error) {
      button.textContent = "重试保存";
      button.disabled = false;
      addMessage("assistant", error.message || "工作流保存失败。", true);
    }
  });
  box.append(label, button);
  return box;
}

function renderEvidence(response) {
  evidenceList.replaceChildren();
  toolCalls.replaceChildren();
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
  evidenceEmpty.hidden = evidenceList.children.length > 0 || toolCalls.children.length > 0;
  toolCalls.hidden = toolCalls.children.length === 0;
  const assets = response.meta?.userContext?.assets;
  if (assets) assetSummary.textContent = `${assets.activeCount || 0} 个活动工作流`;
}

async function submitMessage(message) {
  const text = String(message || "").trim();
  if (!text || sendButton.disabled) return;
  addMessage("user", text);
  input.value = "";
  sendButton.disabled = true;
  status.textContent = "检索中";
  try {
    const response = await apiPost("/agent/chat", {
      message: text,
      pageContext: { page: "assistant", url: window.location.pathname },
    });
    addMessage("assistant", response.answer);
    renderCards(response.cards);
    renderSteps(response.workflowSteps, response.workflowDraft);
    renderEvidence(response);
    status.textContent = response.meta?.readOnly ? "只读结果" : "已完成";
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      addMessage("assistant", "请先登录后使用站内助手。登录完成后可以重新发送刚才的问题。", true);
      document.querySelector('[data-auth-trigger="login"]')?.click();
      status.textContent = "需要登录";
    } else {
      addMessage("assistant", error.message || "助手暂时不可用，请稍后重试。", true);
      status.textContent = "请求失败";
    }
  } finally {
    sendButton.disabled = false;
    input.focus();
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
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => submitMessage(button.dataset.prompt));
});
