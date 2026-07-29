import { getAccessToken } from "./api.js";
import { mergeAnonymousLearningState, recordAnonymousNodeView } from "./anonymous-learning-state.js";
import { safeInternalHref } from "./url-safety.js";
import {
  addLearningFavorite,
  getLearningDashboard,
  getLearningNodeState,
  listLearningFavorites,
  listLearningProgress,
  recordLearningActivity,
  removeLearningFavorite,
  updateLearningProgress,
  updateLearningSection,
} from "./learning-api.js";

let dashboardPromise = null;
let dashboardToken = "";
const STYLE_ID = "learning-state-styles";

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
    .learning-resume-band{margin:18px 0 8px;padding:16px 18px;border:1px solid rgba(15,15,25,.09);border-radius:8px;background:#fff;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;box-shadow:0 8px 24px rgba(31,42,68,.05)}
    .learning-resume-copy{min-width:0}.learning-resume-kicker{font-size:11px;font-weight:700;color:#6d5ef6;margin-bottom:3px}.learning-resume-copy strong{display:block;font-size:16px}.learning-resume-copy span{display:block;color:#6e6e7a;font-size:12px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .learning-resume-meta{display:flex;align-items:center;gap:12px}.learning-resume-progress{font-size:12px;font-weight:700;color:#57606a;white-space:nowrap}.learning-resume-link{height:34px;display:inline-flex;align-items:center;padding:0 12px;border-radius:7px;background:#24292f;color:#fff!important;font-size:12px;font-weight:700}
    .node-learning-state{margin-top:14px;padding-top:14px;border-top:1px solid rgba(15,15,25,.08);display:grid;gap:9px}.node-state-head{display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px}.node-state-head strong{font-size:13px}.node-state-track{height:6px;border-radius:3px;background:#ececf1;overflow:hidden}.node-state-track i{display:block;height:100%;background:#16a36a;border-radius:inherit;transition:width .2s}.node-state-actions{display:flex;flex-wrap:wrap;gap:8px}.node-state-btn{height:32px;padding:0 11px;border:1px solid rgba(15,15,25,.12);border-radius:7px;background:#fff;color:#24292f;font-size:12px;font-weight:700}.node-state-btn:hover{background:#f6f8fa}.node-state-btn:disabled{opacity:.55;cursor:wait}.node-state-btn.is-favorite{color:#cf7b00;background:#fff8e6}.node-state-message{min-height:17px;font-size:12px;color:#57606a}.node-state-message.error{color:#cf222e}
    .km-canvas:not(.has-domain) .km-node.learning-in-progress .km-node-rect{stroke:#0ea5e9;stroke-width:2}.km-canvas:not(.has-domain) .km-node.learning-completed .km-node-rect{stroke:#16a36a;stroke-width:2;fill:#f3fbf7}.km-canvas:not(.has-domain) .km-node.learning-completed .km-node-dot{fill:#16a36a}
    @media(max-width:768px){.nav .brand{white-space:nowrap}.nav .brand>span:last-child{display:none}.learning-resume-band{grid-template-columns:1fr}.learning-resume-meta{justify-content:space-between}.learning-resume-copy span{white-space:normal}.node-state-actions{display:grid;grid-template-columns:1fr 1fr}.node-state-btn{width:100%}}
  `;
  document.head.appendChild(style);
}

function loggedIn() {
  return Boolean(getAccessToken());
}

async function dashboard(force = false) {
  const token = getAccessToken();
  if (!token) {
    dashboardPromise = null;
    dashboardToken = "";
    return null;
  }
  if (force || !dashboardPromise || dashboardToken !== token) {
    const requestToken = token;
    dashboardToken = token;
    dashboardPromise = getLearningDashboard().catch((error) => {
      if (dashboardToken === requestToken) dashboardPromise = null;
      console.warn("Learning dashboard unavailable:", error);
      return null;
    });
  }
  return dashboardPromise;
}

function resumeBand(item) {
  if (!item) return "";
  const percent = Number(item.progressPercent || 0);
  const label = item.reasonCode === "RESUME_IN_PROGRESS" ? "继续学习" : item.reasonCode === "CONTINUE_RECENT" ? "最近阅读" : "推荐起点";
  return `
    <div class="learning-resume-band">
      <div class="learning-resume-copy">
        <div class="learning-resume-kicker">${label}</div>
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.description || "从这里继续你的学习路径")}</span>
      </div>
      <div class="learning-resume-meta">
        ${percent ? `<span class="learning-resume-progress">${percent}%</span>` : ""}
        <a class="learning-resume-link" href="${escapeHtml(safeInternalHref(item.href, "/learn"))}">继续 →</a>
      </div>
    </div>`;
}

export async function hydrateLearningDashboard(isCurrent = () => true) {
  injectStyles();
  const data = await dashboard();
  if (!isCurrent() || !data?.resume) return;
  const heroTop = document.querySelector(".km-hero-top");
  if (heroTop && !document.querySelector(".km-hero .learning-resume-band")) {
    heroTop.insertAdjacentHTML("afterend", resumeBand(data.resume));
  }
  const recent = document.querySelector(".recent-entry");
  if (recent && data.recent?.[0]) {
    recent.href = safeInternalHref(data.recent[0].href, "/settings#learning");
    recent.firstChild.textContent = `最近阅读 · ${data.recent[0].title} `;
  }
}

export async function decorateRoadmapProgress(scope = document, isCurrent = () => true) {
  const data = await dashboard();
  if (!isCurrent() || !data) return;
  const progressResult = await listLearningProgress();
  if (!isCurrent()) return;
  const progress = new Map(progressResult.items.map((item) => [item.nodeSlug, item]));
  scope.querySelectorAll(".km-node[data-node-slug]").forEach((node) => {
    const item = progress.get(node.dataset.nodeSlug);
    node.classList.toggle("learning-in-progress", item?.status === "in_progress");
    node.classList.toggle("learning-completed", item?.status === "completed");
    if (item) node.setAttribute("aria-label", `${node.getAttribute("aria-label") || "学习节点"}，进度 ${item.progressPercent}%`);
  });
}

async function recordActivity(payload, key) {
  if (!loggedIn()) return null;
  return recordLearningActivity(payload, key);
}

function pageActivityKey(slug) {
  const storageKey = `learning_view_${slug}`;
  let value = sessionStorage.getItem(storageKey);
  if (!value) {
    value = `${storageKey}_${Date.now()}`;
    sessionStorage.setItem(storageKey, value);
  }
  return value;
}

export async function hydrateNodeLearningState(slug, nodeData, isCurrent = () => true) {
  injectStyles();
  if (!loggedIn()) {
    if (isCurrent()) recordAnonymousNodeView(slug);
    return;
  }
  await mergeAnonymousLearningState().catch((error) => {
    console.warn("Anonymous learning state import unavailable:", error);
  });
  if (!isCurrent()) return;
  await recordActivity({ nodeSlug: slug, targetType: "learning_node", targetKey: slug, activityType: "view_node", metadata: { page: "learn-node" } }, pageActivityKey(slug));
  if (!isCurrent()) return;
  let [nodeState, favoriteResult] = await Promise.all([
    getLearningNodeState(slug),
    listLearningFavorites({ page_size: 50 }),
  ]);
  if (!isCurrent()) return;
  let progress = nodeState.progress;
  let sectionStates = new Map(nodeState.sections.map((item) => [item.sectionUid, item]));
  let favorite = favoriteResult.items.find((item) => item.targetType === "learning_node" && item.targetKey === slug) || null;
  const actions = document.querySelector(".detail-actions");
  if (!actions || document.querySelector(".node-learning-state")) return;
  actions.insertAdjacentHTML("afterend", `
    <div class="node-learning-state" aria-live="polite">
      <div class="node-state-head"><strong data-learning-status>${progress?.status === "completed" ? "已完成" : progress ? "学习中" : "尚未开始"}</strong><span data-learning-percent>${progress?.progressPercent || 0}%</span></div>
      <div class="node-state-track"><i data-learning-track style="width:${progress?.progressPercent || 0}%"></i></div>
      <div class="node-state-actions">
        <button class="node-state-btn" type="button" data-mark-progress>${progress?.status === "completed" ? "重新学习" : progress ? "更新到 50%" : "标记为学习中"}</button>
        <button class="node-state-btn" type="button" data-complete-node>✓ 标记完成</button>
        <button class="node-state-btn ${favorite ? "is-favorite" : ""}" type="button" data-favorite-node>${favorite ? "★ 已收藏" : "☆ 收藏"}</button>
      </div>
      <div class="node-state-message" data-learning-message></div>
    </div>`);

  const render = () => {
    document.querySelector("[data-learning-status]").textContent = progress?.status === "completed" ? "已完成" : progress ? "学习中" : "尚未开始";
    document.querySelector("[data-learning-percent]").textContent = `${progress?.progressPercent || 0}%`;
    document.querySelector("[data-learning-track]").style.width = `${progress?.progressPercent || 0}%`;
    document.querySelector("[data-mark-progress]").textContent = progress?.status === "completed" ? "重新学习" : progress ? "更新到 50%" : "标记为学习中";
  };
  const renderSections = () => {
    document.querySelectorAll("[data-section-uid]").forEach((row) => {
      const button = row.querySelector("[data-section-toggle]");
      if (!button) return;
      const state = sectionStates.get(row.dataset.sectionUid);
      button.hidden = false;
      button.classList.toggle("is-complete", Boolean(state?.isCompleted));
      button.textContent = state?.isCompleted ? "已完成" : "完成";
      button.setAttribute("aria-pressed", String(Boolean(state?.isCompleted)));
    });
  };
  const refreshNodeState = async () => {
    nodeState = await getLearningNodeState(slug);
    progress = nodeState.progress;
    sectionStates = new Map(nodeState.sections.map((item) => [item.sectionUid, item]));
    render();
    renderSections();
  };
  renderSections();
  const updateProgress = async (percent, status) => {
    const buttons = document.querySelectorAll(".node-state-btn");
    const message = document.querySelector("[data-learning-message]");
    buttons.forEach((button) => { button.disabled = true; });
    message.textContent = "正在保存进度...";
    message.classList.remove("error");
    try {
      const result = await updateLearningProgress(slug, { progressPercent: percent, status, expectedVersion: progress?.version });
      progress = result.progress;
      await refreshNodeState();
      dashboardPromise = null;
      message.textContent = "进度已保存";
    } catch (error) {
      if (error.code === "PROGRESS_CONFLICT") {
        const latest = await listLearningProgress();
        progress = latest.items.find((item) => item.nodeSlug === slug) || null;
        render();
        message.textContent = "进度已在其他页面更新，已加载最新状态。";
      } else {
        message.textContent = error.message || "进度保存失败，请重试。";
      }
      message.classList.add("error");
    } finally {
      buttons.forEach((button) => { button.disabled = false; });
    }
  };
  document.querySelector("[data-mark-progress]").addEventListener("click", () => {
    const percent = progress?.status === "completed" ? 5 : progress ? Math.max(50, progress.progressPercent) : 5;
    updateProgress(percent, "in_progress");
  });
  document.querySelector("[data-complete-node]").addEventListener("click", () => updateProgress(100, "completed"));
  document.querySelectorAll("[data-section-toggle]").forEach((button) => {
    button.addEventListener("click", async () => {
      const row = button.closest("[data-section-uid]");
      const sectionUid = row.dataset.sectionUid;
      const state = sectionStates.get(sectionUid);
      const message = document.querySelector("[data-learning-message]");
      button.disabled = true;
      message.textContent = "正在保存章节进度...";
      message.classList.remove("error");
      try {
        const result = await updateLearningSection(
          slug, sectionUid, { isCompleted: !state?.isCompleted, expectedVersion: state?.version || 0 },
        );
        sectionStates.set(sectionUid, result.section);
        progress = result.progress;
        dashboardPromise = null;
        render();
        renderSections();
        message.textContent = result.section.isCompleted ? "章节已完成" : "章节已设为未完成";
      } catch (error) {
        if (error.code === "SECTION_PROGRESS_CONFLICT") {
          await refreshNodeState();
          message.textContent = "章节进度已在其他页面更新，已加载最新状态。";
        } else {
          message.textContent = error.message || "章节进度保存失败，请重试。";
        }
        message.classList.add("error");
      } finally {
        button.disabled = false;
      }
    });
  });
  document.querySelector("[data-favorite-node]").addEventListener("click", async (event) => {
    const message = document.querySelector("[data-learning-message]");
    const button = event.currentTarget;
    button.disabled = true;
    try {
      if (favorite) {
        await removeLearningFavorite(favorite.favoriteUid);
        favorite = null;
      } else {
        favorite = (await addLearningFavorite("learning_node", slug)).favorite;
      }
      button.classList.toggle("is-favorite", Boolean(favorite));
      button.textContent = favorite ? "★ 已收藏" : "☆ 收藏";
      message.textContent = favorite ? "已加入收藏" : "已移出收藏";
      message.classList.remove("error");
      dashboardPromise = null;
    } catch (error) {
      message.textContent = error.message || "收藏操作失败，请重试。";
      message.classList.add("error");
    } finally {
      button.disabled = false;
    }
  });
  document.querySelectorAll("[data-start-learning]").forEach((link) => {
    if (progress) link.textContent = "继续学习 →";
    link.addEventListener("click", () => {
      recordActivity({ nodeSlug: slug, targetType: "learning_material", targetKey: nodeData.mainMaterial.materialUid, activityType: "start_material", metadata: { source: "primary" } }, `start_${slug}_${Date.now()}`);
      if (!progress) updateProgress(5, "in_progress");
    });
  });
}
