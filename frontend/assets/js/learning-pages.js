import { apiGet, getAccessToken } from "./api.js";
import { AssistantSessionEpoch } from "./assistant-session-epoch.js";
import { getLearningNode, getLearningRoadmap, listLearningResources } from "./learning-api.js";
import { decorateRoadmapProgress, hydrateLearningDashboard, hydrateNodeLearningState } from "./learning-state.js";
import { $, $$, bindReveal, bindSpotlight, escapeHtml } from "./page-shell.js";
import { safeHttpHref, safeInternalHref } from "./url-safety.js";
import { feedbackKindForError, feedbackMarkup, renderFeedback } from "./ui-feedback.js";
import {
  applyLearningResourcePreferences,
  getConsumerPreferences,
} from "./user-preference-consumers.js";

const TOOL_ICON_STYLE_ID = "ai-nav-tool-icon-style";

function accessLabel(type = "external") {
  return type === "cn" ? "国内可访问" : "外网";
}

function injectToolIconStyles() {
  if (document.getElementById(TOOL_ICON_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = TOOL_ICON_STYLE_ID;
  style.textContent = `
    .brand-icon{background:#fff!important;color:#24292f!important;border:1px solid #d8dee4!important;box-shadow:0 1px 2px rgba(31,35,40,.06)!important;overflow:hidden}
    .brand-icon img{width:64%;height:64%;object-fit:contain}
    .marquee-fav.brand-icon img{width:22px;height:22px}.latest-logo.brand-icon img,.tool-logo.brand-icon img{width:28px;height:28px}
  `;
  document.head.appendChild(style);
}

function bindToolIconFallbacks(scope = document) {
  $$("img[data-fallbacks]", scope).forEach((img) => {
    img.addEventListener("error", () => {
      const fallbacks = JSON.parse(img.dataset.fallbacks || "[]");
      const next = fallbacks.shift();
      if (next) {
        img.dataset.fallbacks = JSON.stringify(fallbacks);
        img.src = next;
        return;
      }
      img.parentElement.textContent = img.dataset.mark || "AI";
    }, { once: false });
  });
}

function toolIcon(tool, className) {
  const fallback = escapeHtml(tool.mark || tool.name?.slice(0, 2) || "AI");
  const fallbacks = [tool.iconUrl, ...(tool.iconFallbacks || [])]
    .map((value) => safeHttpHref(value, ""))
    .filter(Boolean);
  if (!fallbacks.length) return `<div class="${className} ${escapeHtml(tool.logoClass || "")}">${fallback}</div>`;
  return `<div class="${className} brand-icon"><img src="${escapeHtml(fallbacks[0])}" data-fallbacks="${escapeHtml(JSON.stringify(fallbacks.slice(1)))}" data-mark="${fallback}" alt="" loading="lazy"></div>`;
}

function nodeSvg(node) {
  const href = `learn-node.html?slug=${encodeURIComponent(node.slug)}`;
  return `
    <g class="km-node" data-node-slug="${escapeHtml(node.slug)}" transform="translate(${node.x},${node.y})" role="link" tabindex="0">
      <rect class="km-node-rect" width="${node.width}" height="${node.height}" rx="8"/>
      <circle class="km-node-port" cx="0" cy="24" r="4"/><circle class="km-node-port" cx="${node.width}" cy="24" r="4"/>
      <circle class="km-node-dot" cx="25" cy="24" r="5" fill="${escapeHtml(node.color)}"/>
      <text class="km-node-text" x="42" y="21">${escapeHtml(node.title)}</text>
      <text class="km-node-sub" x="42" y="36">${escapeHtml(node.subtitle)}</text>
      <a href="${href}" aria-label="${escapeHtml(node.title)}"></a>
    </g>`;
}

function wireRoadmapDomain(canvas, data) {
  const tabs = $$(".line-tab, .roadmap-tab", document);
  const apply = (domain, color, glow) => {
    const slugs = data.domainNodes[domain] || [];
    canvas.classList.toggle("has-domain", slugs.length > 0);
    $$(".km-node", canvas).forEach((node) => {
      const selected = slugs.includes(node.dataset.nodeSlug);
      node.classList.toggle("domain-selected", selected);
      if (selected) {
        node.style.setProperty("--domain-color", color);
        node.style.setProperty("--domain-glow", glow);
      } else {
        node.style.removeProperty("--domain-color");
        node.style.removeProperty("--domain-glow");
      }
    });
  };
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      apply(tab.dataset.domain, tab.style.getPropertyValue("--domain-color"), tab.style.getPropertyValue("--domain-glow"));
    });
  });
  const active = tabs.find((tab) => tab.classList.contains("active") && tab.dataset.domain) || tabs[0];
  if (active) apply(active.dataset.domain, active.style.getPropertyValue("--domain-color"), active.style.getPropertyValue("--domain-glow"));
}

async function hydrateRoadmap() {
  const canvas = $(".km-canvas");
  const svg = $(".km-svg");
  if (!canvas || !svg) return;
  try {
    const data = await getLearningRoadmap();
    svg.setAttribute("viewBox", data.viewBox);
    svg.innerHTML = `
      ${data.edges.map((edge) => `<path class="km-link ${edge.lineType === "thin" ? "km-link-thin" : ""}" d="${escapeHtml(edge.pathD)}"/>`).join("")}
      ${data.nodes.map(nodeSvg).join("")}`;
    $$(".km-node", svg).forEach((node) => {
      const slug = node.dataset.nodeSlug;
      const open = () => { window.location.href = `learn-node.html?slug=${encodeURIComponent(slug)}`; };
      node.addEventListener("click", open);
      node.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") open();
      });
    });
    wireRoadmapDomain(canvas, data);
    return data;
  } catch (error) {
    console.warn("Roadmap API fallback:", error);
    return null;
  }
}

function resourceCard(item) {
  return `
    <a href="${escapeHtml(safeInternalHref(item.href, "learn.html"))}" class="resource-card" data-spotlight>
      <div class="resource-cover ${escapeHtml(item.coverTheme)}">
        <div class="resource-cover-label">${escapeHtml(item.coverLabel)}</div>
        <div class="resource-cover-text">${escapeHtml(item.coverText)}</div>
      </div>
      <div class="resource-info">
        <div class="resource-title">${escapeHtml(item.title)}</div>
        <div class="resource-desc">${escapeHtml(item.description)}</div>
      </div>
    </a>`;
}

async function hydrateLearningResources(domain = "", isCurrent = () => true) {
  const grid = $(".resource-grid");
  if (!grid) return;
  try {
    const [{ items }, preferences] = await Promise.all([
      listLearningResources(domain),
      getConsumerPreferences("learning"),
    ]);
    if (!isCurrent()) return;
    const visibleItems = applyLearningResourcePreferences(items, preferences);
    grid.innerHTML = visibleItems.map(resourceCard).join("");
    bindSpotlight(grid);
  } catch (error) {
    if (!isCurrent()) return;
    console.warn("Learning resources API fallback:", error);
    grid.innerHTML = feedbackMarkup({
      kind: feedbackKindForError(error),
      title: error.code === "API_OFFLINE" ? "当前处于离线状态" : "学习资源暂时无法加载",
      message: "学习地图仍可浏览，恢复连接后可以重新加载资源。",
      actionLabel: "重新加载",
      actionKey: "reload-learning-resources",
    });
    grid.querySelector("[data-feedback-action]")?.addEventListener("click", () => location.reload());
  }
}

function resetLearningPageUserState() {
  document.querySelector(".km-hero .learning-resume-band")?.remove();
  document.querySelectorAll(".km-node[data-node-slug]").forEach((node) => {
    node.classList.remove("learning-in-progress", "learning-completed");
    node.removeAttribute("aria-label");
  });
  const recent = document.querySelector(".recent-entry");
  if (recent) {
    recent.setAttribute("href", "#");
    if (recent.firstChild) recent.firstChild.textContent = "最近阅读 ";
  }
}

function resetNodeLearningState(outline, mainMaterial, resources) {
  document.querySelector(".node-learning-state")?.remove();
  const outlineEl = $("[data-outline]");
  if (outlineEl) {
    outlineEl.innerHTML = outline.length
      ? renderOutline(outline)
      : feedbackMarkup({ message: "该节点暂未维护目录。", compact: true });
  }
  renderNodeResourceList(mainMaterial, resources);
}

function observeAuthenticatedLearning(
  authReady,
  hydrate,
  hydrateAnonymous = null,
  reset = null,
) {
  const epoch = new AssistantSessionEpoch(getAccessToken());
  let authenticatedHydrated = false;
  let hydrationPromise = null;
  const reportError = (error) => {
    console.warn("Authenticated learning state unavailable:", error);
  };
  const hydrateAuthenticated = () => {
    if (authenticatedHydrated) return hydrationPromise;
    const operation = epoch.beginOperation();
    authenticatedHydrated = true;
    hydrationPromise = Promise.resolve()
      .then(() => hydrate(operation.isCurrent))
      .catch((error) => {
        if (operation.isCurrent()) authenticatedHydrated = false;
        throw error;
      })
      .finally(operation.finish);
    return hydrationPromise;
  };
  const transitionIdentity = () => {
    const changed = epoch.transition(getAccessToken());
    if (changed) {
      authenticatedHydrated = false;
      hydrationPromise = null;
      reset?.();
    }
    return changed;
  };

  window.addEventListener("ai-nav-auth-changed", (event) => {
    transitionIdentity();
    if (!event.detail?.authenticated) {
      authenticatedHydrated = false;
      hydrationPromise = null;
      return;
    }
    void hydrateAuthenticated().catch(reportError);
  });

  void Promise.resolve(authReady)
    .then((user) => {
      transitionIdentity();
      if (user || getAccessToken()) return hydrateAuthenticated();
      return hydrateAnonymous?.();
    })
    .catch(reportError);
}

export async function initLearnPage({ authReady = Promise.resolve(null) } = {}) {
  const publicHydration = Promise.all([
    hydrateRoadmap(),
    hydrateLearningResources(""),
  ]);
  observeAuthenticatedLearning(authReady, async (isCurrent) => {
    await publicHydration;
    if (!isCurrent()) return;
    await Promise.all([
      decorateRoadmapProgress($(".km-canvas") || document, isCurrent),
      hydrateLearningResources("", isCurrent),
      hydrateLearningDashboard(isCurrent),
    ]);
  }, null, resetLearningPageUserState);
  await publicHydration;
}

function latestToolCard(tool) {
  return `<a class="latest-card" href="${escapeHtml(safeHttpHref(tool.officialUrl))}" target="_blank" rel="noopener noreferrer">
    ${toolIcon(tool, "latest-logo")}
    <div><strong>${escapeHtml(tool.name)}</strong><span>${escapeHtml(tool.description)}</span><em>${escapeHtml(tool.tag)}</em></div>
  </a>`;
}

async function hydrateHomeTools() {
  const track = $(".tools-marquee-track");
  if (!track) return null;
  try {
    const [{ items }, catalog] = await Promise.all([
      apiGet("/tools/latest", { limit: 12 }),
      apiGet("/tools", { page: 1, page_size: 1 }),
    ]);
    const normalized = items.map((item) => {
      const tool = item.tool || item;
      return {
        name: item.displayName || tool.name,
        description: item.provider || tool.description,
        tag: item.label || tool.tags?.[0] || "",
        officialUrl: tool.url,
        iconUrl: tool.icon,
        iconFallbacks: tool.iconFallbacks || [],
        mark: item.mark || tool.mark,
        logoClass: item.logoClass || tool.logoClass,
      };
    });
    const cards = normalized.concat(normalized).map((tool) => `
      <a href="${escapeHtml(safeHttpHref(tool.officialUrl, "tools.html"))}" target="_blank" rel="noopener noreferrer" class="marquee-card">
        ${toolIcon(tool, "marquee-fav")}
        <div><div class="marquee-name">${escapeHtml(tool.name)}</div><div class="marquee-maker">${escapeHtml(tool.description)}</div></div>
        <div class="marquee-cat">${escapeHtml(tool.tag)}</div>
      </a>`).join("");
    track.innerHTML = cards;
    bindToolIconFallbacks(track);
    return { total: catalog.total, items: normalized };
  } catch (error) {
    console.warn("Home tools API fallback:", error);
    return null;
  }
}

function updateHomeStats(roadmap, tools) {
  const values = {
    learning: roadmap?.nodes?.length,
    tools: tools?.total,
    domains: roadmap ? Object.keys(roadmap.domainNodes || {}).length : null,
  };
  Object.entries(values).forEach(([key, value]) => {
    const target = document.querySelector(`[data-stat="${key}"]`);
    if (target && Number.isFinite(value)) target.dataset.target = String(value);
  });
}

function resourceLink(item) {
  const badges = [];
  const unavailable = item.linkStatus === "unavailable";
  if (item.isPrimary) badges.push('<span class="resource-badge primary">主资料</span>');
  badges.push(`<span class="resource-badge ${item.accessType === "cn" ? "cn" : "external"}">${escapeHtml(accessLabel(item.accessType))}</span>`);
  if (unavailable) badges.push('<span class="resource-badge unavailable">链接维护中</span>');
  const href = unavailable ? "#" : safeHttpHref(item.url);
  return `<a href="${escapeHtml(href)}" ${unavailable ? 'aria-disabled="true"' : 'target="_blank" rel="noopener noreferrer"'} class="resource-link${unavailable ? " is-unavailable" : ""}">
    <div class="resource-link-icon" style="background:${escapeHtml(item.accentColor || "#7C5CFF")}22;color:${escapeHtml(item.accentColor || "#7C5CFF")}">↗</div>
    <div class="resource-link-info"><div class="resource-link-name">${escapeHtml(item.title)}${badges.join("")}</div><div class="resource-link-meta">${escapeHtml(item.linkType || item.resourceType || "resource")} · ${escapeHtml(item.description)}</div></div>
    <div class="resource-link-arrow">→</div>
  </a>`;
}

function setText(selector, value, scope = document) {
  const targets = $$(selector, scope);
  targets.forEach((target) => { target.textContent = value ?? ""; });
}

function setExternalHref(selector, value, linkStatus = "unchecked", scope = document) {
  const targets = $$(selector, scope);
  targets.forEach((target) => {
    const href = linkStatus === "unavailable" ? "" : safeHttpHref(value, "");
    target.href = href || "#";
    target.toggleAttribute("aria-disabled", !href);
    if (!href) target.removeAttribute("target");
  });
}

function renderOverview(overview, material, outline) {
  const firstItems = outline.slice(0, 4).map((item) => `<li>${escapeHtml(item.title)}：${escapeHtml(item.description)}</li>`).join("");
  return `
    <div class="content-section">
      <h3 class="content-section-title">${escapeHtml(overview.title)}</h3>
      <p>${escapeHtml(overview.body)}</p>
    </div>
    <div class="content-section">
      <h3 class="content-section-title">主学习资料能帮你解决什么</h3>
      <p>${escapeHtml(material.description)}</p>
      <ul class="content-list">${firstItems}</ul>
    </div>`;
}

function renderOutline(items) {
  if (!items.length) return '<div class="empty-state">该节点暂未维护目录。</div>';
  return items.map((item) => `
    <div class="toc-item" data-section-uid="${escapeHtml(item.sectionUid)}">
      <a class="toc-main" href="${escapeHtml(safeHttpHref(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">
        <span class="toc-num">${String(item.chapterNo).padStart(2, "0")}-${String(item.sectionNo).padStart(2, "0")}</span>
        <span class="toc-title"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.description)}</span></span>
        <span class="toc-meta">${escapeHtml(`${item.durationMinutes} min`)}</span>
      </a>
      <button class="toc-complete-btn" type="button" data-section-toggle hidden aria-label="标记 ${escapeHtml(item.title)} 为已完成">完成</button>
    </div>`).join("");
}

function renderNodeResourceList(mainMaterial, resources, preferences = {}) {
  const list = $("[data-resources]");
  if (!list) return;
  const allResources = [
    {
      title: mainMaterial.title,
      description: `主学习资料 · ${mainMaterial.provider}`,
      url: mainMaterial.url,
      linkType: mainMaterial.materialType,
      accessType: mainMaterial.accessType,
      linkStatus: mainMaterial.linkStatus,
      isPrimary: true,
      accentColor: "#7C5CFF",
    },
    ...applyLearningResourcePreferences(resources, preferences),
  ];
  list.innerHTML = allResources.length
    ? allResources.map(resourceLink).join("")
    : feedbackMarkup({ message: "该节点暂未维护补充资料。", compact: true });
}

export async function initNodePage({ authReady = Promise.resolve(null) } = {}) {
  const params = new URLSearchParams(location.search);
  const slug = params.get("slug") || "ai-literacy";
  try {
    const nodePayload = await getLearningNode(slug);
    const { node, mainMaterial, overview, outline, resources, tags, stats, navigation } = nodePayload;
    document.title = `${node.title} · 节点详情 · AI 知识导航`;
    setText("[data-node-title]", node.title);
    setText("[data-node-description]", `${node.title}：${node.subtitle}。${mainMaterial.description}`);
    setText("[data-cover-label]", mainMaterial.coverLabel);
    setText("[data-cover-name]", mainMaterial.coverText || node.title);
    setText("[data-material-provider]", mainMaterial.provider);
    setText("[data-material-title]", mainMaterial.title);
    setText("[data-material-type]", mainMaterial.materialType);
    setText("[data-material-language]", mainMaterial.language);
    setText("[data-material-access]", accessLabel(mainMaterial.accessType));
    setText("[data-material-description]", mainMaterial.description);
    setText("[data-stat-chapters]", stats.chapterCount);
    setText("[data-stat-sections]", stats.sectionCount);
    setText("[data-stat-duration]", stats.suggestedDuration);
    setExternalHref("[data-start-learning]", mainMaterial.startUrl || mainMaterial.url, mainMaterial.linkStatus);
    setExternalHref("[data-main-material]", mainMaterial.url, mainMaterial.linkStatus);
    const cover = $("[data-cover]");
    if (cover) {
      cover.className = `cover ${escapeHtml(mainMaterial.coverTheme || "")}`;
    }
    const overviewEl = $("[data-overview]");
    if (overviewEl) overviewEl.innerHTML = renderOverview(overview, mainMaterial, outline);
    const outlineEl = $("[data-outline]");
    if (outlineEl) outlineEl.innerHTML = outline.length
      ? renderOutline(outline)
      : feedbackMarkup({ message: "该节点暂未维护目录。", compact: true });
    renderNodeResourceList(mainMaterial, resources);
    const tagsEl = $("[data-tags]");
    if (tagsEl) tagsEl.innerHTML = tags.map((tag) => `<span class="side-tag">${escapeHtml(tag)}</span>`).join("");
    const navEl = $("[data-node-nav]");
    if (navEl) {
      const links = [];
      if (navigation.previous) links.push(`<a class="side-link" href="learn-node.html?slug=${escapeHtml(navigation.previous.slug)}">← ${escapeHtml(navigation.previous.title)}</a>`);
      if (navigation.next) links.push(`<a class="side-link" href="learn-node.html?slug=${escapeHtml(navigation.next.slug)}">→ ${escapeHtml(navigation.next.title)}</a>`);
      navEl.innerHTML = links.length ? links.join("") : '<p class="side-text">当前节点暂无相邻路线。</p>';
    }
    bindReveal(document);
    observeAuthenticatedLearning(
      authReady,
      async (isCurrent) => {
        await Promise.all([
          hydrateNodeLearningState(slug, { node, mainMaterial, stats, outline }, isCurrent),
          getConsumerPreferences("learning").then((preferences) => {
            if (!isCurrent()) return;
            renderNodeResourceList(mainMaterial, resources, preferences);
          }),
        ]);
      },
      () => hydrateNodeLearningState(slug, { node, mainMaterial, stats, outline }),
      () => resetNodeLearningState(outline, mainMaterial, resources),
    );
  } catch (error) {
    console.warn("Node API fallback:", error);
    document.title = "学习节点暂不可用 · AI 知识导航";
    $(".detail-head")?.classList.add("is-error");
    setText("[data-node-title]", "学习节点暂不可用");
    setText("[data-node-description]", "当前节点不存在或内容暂时无法读取。");
    const content = $(".detail-content");
    if (content) {
      renderFeedback(content, {
        kind: feedbackKindForError(error),
        title: error.code === "API_OFFLINE" ? "当前处于离线状态" : "未能加载学习内容",
        message: error.message || "请稍后重试，公开学习路线仍可正常访问。",
        actionLabel: "重新加载",
        actionKey: "retry-node",
        onAction: () => location.reload(),
      });
    }
  }
}

export async function initHomePage() {
  injectToolIconStyles();
  const [roadmap, tools] = await Promise.all([
    hydrateRoadmap(),
    hydrateHomeTools(),
  ]);
  updateHomeStats(roadmap, tools);
}
