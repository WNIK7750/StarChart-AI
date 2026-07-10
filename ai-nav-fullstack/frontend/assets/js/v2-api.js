import { apiGet } from "./api.js";
import { initAuthUI } from "./auth-ui.js";
import { initSiteSearch } from "./site-search.js";

const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));
const TOOL_ICON_STYLE_ID = "ai-nav-tool-icon-style";

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function accessLabel(type = "external") {
  return type === "cn" ? "国内可访问" : "外网";
}

function bindSpotlight(scope = document) {
  $$("[data-spotlight]", scope).forEach((card) => {
    card.addEventListener("mousemove", (event) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${((event.clientX - rect.left) / rect.width) * 100}%`);
      card.style.setProperty("--my", `${((event.clientY - rect.top) / rect.height) * 100}%`);
    });
  });
}

function bindReveal(scope = document) {
  if (!("IntersectionObserver" in window)) {
    $$(".reveal", scope).forEach((el) => el.classList.add("in"));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: "0px 0px -80px 0px" });
  $$(".reveal", scope).forEach((el) => {
    if (!el.classList.contains("in")) io.observe(el);
  });
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
  const fallbacks = [tool.iconUrl, ...(tool.iconFallbacks || [])].filter(Boolean);
  if (!fallbacks.length) return `<div class="${className} ${escapeHtml(tool.logoClass || "")}">${fallback}</div>`;
  return `<div class="${className} brand-icon"><img src="${escapeHtml(fallbacks[0])}" data-fallbacks="${escapeHtml(JSON.stringify(fallbacks.slice(1)))}" data-mark="${fallback}" alt="" loading="lazy"></div>`;
}

async function hydrateNavigation(activeCode) {
  const navs = $$(".nav-links, .top-nav");
  if (!navs.length) return;
  try {
    const { items } = await apiGet("/navigation");
    const html = items.map((item) => {
      const active = item.code === activeCode ? "active" : "";
      return `<a href="${escapeHtml(item.href)}" class="${active}">${escapeHtml(item.label)}</a>`;
    }).join("");
    navs.forEach((nav) => { nav.innerHTML = html; });
  } catch (error) {
    console.warn("Navigation API fallback:", error);
  }
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
      node.style.setProperty("--domain-color", color);
      node.style.setProperty("--domain-glow", glow);
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
    const data = await apiGet("/learning/roadmap");
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
  } catch (error) {
    console.warn("Roadmap API fallback:", error);
  }
}

function resourceCard(item) {
  return `
    <a href="${escapeHtml(item.href)}" class="resource-card" data-spotlight>
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

async function hydrateLearningResources(domain = "") {
  const grid = $(".resource-grid");
  if (!grid) return;
  try {
    const { items } = await apiGet("/learning/resources", { domain });
    grid.innerHTML = items.map(resourceCard).join("");
    bindSpotlight(grid);
  } catch (error) {
    console.warn("Learning resources API fallback:", error);
  }
}

async function hydrateLearnPage() {
  await hydrateRoadmap();
  await hydrateLearningResources("");
}

function latestToolCard(tool) {
  return `<a class="latest-card" href="${escapeHtml(tool.officialUrl || "#")}" target="_blank" rel="noopener">
    ${toolIcon(tool, "latest-logo")}
    <div><strong>${escapeHtml(tool.name)}</strong><span>${escapeHtml(tool.description)}</span><em>${escapeHtml(tool.tag)}</em></div>
  </a>`;
}

async function hydrateHomeTools() {
  const track = $(".tools-marquee-track");
  if (!track) return;
  try {
    const { items } = await apiGet("/tools/latest", { limit: 12 });
    const cards = items.concat(items).map((tool) => `
      <a href="${escapeHtml(tool.officialUrl || "tools.html")}" target="_blank" rel="noopener" class="marquee-card">
        ${toolIcon(tool, "marquee-fav")}
        <div><div class="marquee-name">${escapeHtml(tool.name)}</div><div class="marquee-maker">${escapeHtml(tool.description)}</div></div>
        <div class="marquee-cat">${escapeHtml(tool.tag)}</div>
      </a>`).join("");
    track.innerHTML = cards;
    bindToolIconFallbacks(track);
  } catch (error) {
    console.warn("Home tools API fallback:", error);
  }
}

function toolCard(tool) {
  return `<a href="${escapeHtml(tool.officialUrl || "#")}" target="_blank" rel="noopener" class="tool-card" data-tool="${escapeHtml(tool.name)}" data-spotlight>
    <div class="tool-main">
      ${toolIcon(tool, "tool-logo")}
      <div class="tool-info"><strong>${escapeHtml(tool.name)}</strong><p>${escapeHtml(tool.description)}</p></div>
    </div>
    <div class="tool-meta"><span class="tag">${escapeHtml(tool.subcategory)}</span><span class="tool-arrow">›</span></div>
  </a>`;
}

function subnav(category, activeSub) {
  return category.subcategories.map((sub) => {
    const active = sub === activeSub ? "active" : "";
    return `<button class="${active}" data-sub-cat="${escapeHtml(category.code)}" data-sub="${escapeHtml(sub)}">${escapeHtml(sub)}</button>`;
  }).join("");
}

async function hydrateToolsPage() {
  const sections = $("#toolsSections");
  if (!sections) return;
  try {
    const [{ items: categories }, { items: latest }] = await Promise.all([
      apiGet("/tools/categories"),
      apiGet("/tools/latest", { limit: 10 }),
    ]);
    const latestTrack = $("#latestTrack");
    if (latestTrack) latestTrack.innerHTML = latest.concat(latest).map(latestToolCard).join("");
    if (latestTrack) bindToolIconFallbacks(latestTrack);
    const state = { q: "", freeOnly: false, activeSub: {} };
    const render = async () => {
      const nav = $("#categoryNav");
      if (nav) {
        nav.innerHTML = "<h3>分区跳转</h3>" + categories.map((cat) => `<button data-cat="${cat.code}"><span>${cat.icon}</span>${cat.name}</button>`).join("");
        $$("[data-cat]", nav).forEach((btn) => btn.addEventListener("click", () => {
          const target = $(`#section-${btn.dataset.cat}`);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        }));
      }
      const groups = await Promise.all(categories.map(async (cat) => {
        const activeSub = state.q || state.freeOnly ? "全部" : (state.activeSub[cat.code] || "全部");
        const { items } = await apiGet("/tools", {
          category: cat.code,
          subcategory: activeSub,
          q: state.q,
          free_only: state.freeOnly,
          page_size: 50,
        });
        if (!items.length) return "";
        return `<section class="category-section" id="section-${escapeHtml(cat.code)}">
          <div class="category-top"><div class="category-title"><h2>${escapeHtml(cat.name)}</h2><p>${escapeHtml(cat.description)}</p></div><div class="category-count">${items.length} 个工具</div></div>
          <div class="section-subnav">${subnav(cat, activeSub)}</div>
          <div class="category-tools">${items.map(toolCard).join("")}</div>
        </section>`;
      }));
      sections.innerHTML = groups.join("") || '<div class="empty">没有找到匹配工具，换个关键词试试。</div>';
      $$("[data-sub-cat]", sections).forEach((btn) => btn.addEventListener("click", () => {
        state.activeSub[btn.dataset.subCat] = btn.dataset.sub;
        render();
      }));
      bindSpotlight(sections);
      bindReveal(sections);
      bindToolIconFallbacks(sections);
    };
    $("#searchForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      state.q = $("#searchInput")?.value.trim() || "";
      render();
      $("#directory")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    $$("[data-query]").forEach((btn) => btn.addEventListener("click", () => {
      state.q = btn.dataset.query;
      const input = $("#searchInput");
      if (input) input.value = state.q;
      render();
    }));
    $("[data-hot='free']")?.addEventListener("click", () => {
      state.freeOnly = !state.freeOnly;
      render();
    });
    await render();
  } catch (error) {
    console.warn("Tools API fallback:", error);
  }
}

function resourceLink(item) {
  const badges = [];
  if (item.isPrimary) badges.push('<span class="resource-badge primary">主资料</span>');
  badges.push(`<span class="resource-badge ${item.accessType === "cn" ? "cn" : "external"}">${escapeHtml(accessLabel(item.accessType))}</span>`);
  return `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener" class="resource-link">
    <div class="resource-link-icon" style="background:${escapeHtml(item.accentColor || "#7C5CFF")}22;color:${escapeHtml(item.accentColor || "#7C5CFF")}">↗</div>
    <div class="resource-link-info"><div class="resource-link-name">${escapeHtml(item.title)}${badges.join("")}</div><div class="resource-link-meta">${escapeHtml(item.linkType || item.resourceType || "resource")} · ${escapeHtml(item.description)}</div></div>
    <div class="resource-link-arrow">→</div>
  </a>`;
}

function setText(selector, value, scope = document) {
  const targets = $$(selector, scope);
  targets.forEach((target) => { target.textContent = value ?? ""; });
}

function setHref(selector, value, scope = document) {
  const targets = $$(selector, scope);
  targets.forEach((target) => {
    target.href = value || "#";
    target.toggleAttribute("aria-disabled", !value);
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
    <a class="toc-item" href="${escapeHtml(item.sourceUrl || "#")}" target="_blank" rel="noopener">
      <span class="toc-num">${String(item.chapterNo).padStart(2, "0")}-${String(item.sectionNo).padStart(2, "0")}</span>
      <span class="toc-title"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.description)}</span></span>
      <span class="toc-meta">${escapeHtml(`${item.durationMinutes} min`)}</span>
    </a>`).join("");
}

async function hydrateNodePage() {
  const params = new URLSearchParams(location.search);
  const slug = params.get("slug") || "ai-literacy";
  try {
    const { node, mainMaterial, overview, outline, resources, tags, stats, navigation } = await apiGet(`/learning/nodes/${slug}`);
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
    setHref("[data-start-learning]", mainMaterial.startUrl || mainMaterial.url);
    setHref("[data-main-material]", mainMaterial.url);
    const cover = $("[data-cover]");
    if (cover) {
      cover.className = `cover ${escapeHtml(mainMaterial.coverTheme || "")}`;
    }
    const overviewEl = $("[data-overview]");
    if (overviewEl) overviewEl.innerHTML = renderOverview(overview, mainMaterial, outline);
    const outlineEl = $("[data-outline]");
    if (outlineEl) outlineEl.innerHTML = renderOutline(outline);
    const list = $("[data-resources]");
    if (list) {
      const allResources = [
        {
          title: mainMaterial.title,
          description: `主学习资料 · ${mainMaterial.provider}`,
          url: mainMaterial.url,
          linkType: mainMaterial.materialType,
          accessType: mainMaterial.accessType,
          isPrimary: true,
          accentColor: "#7C5CFF",
        },
        ...resources,
      ];
      list.innerHTML = allResources.length ? allResources.map(resourceLink).join("") : '<div class="empty-state">该节点暂未维护补充资料。</div>';
    }
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
  } catch (error) {
    console.warn("Node API fallback:", error);
    setText("[data-node-description]", "节点资料加载失败，请稍后重试。");
  }
}

const page = document.body.dataset.page || location.pathname.split("/").pop().replace(".html", "");
injectToolIconStyles();
await hydrateNavigation(page === "v2-light-concept" || page === "index" ? "home" : page === "learn-node" ? "learn" : page);
initSiteSearch();
await initAuthUI();
if (location.pathname.endsWith("/learn.html")) await hydrateLearnPage();
if (location.pathname.endsWith("/index.html") || location.pathname.endsWith("/")) {
  await hydrateRoadmap();
  await hydrateHomeTools();
}
if (location.pathname.endsWith("/tools.html") && document.body.dataset.apiTools === "true") await hydrateToolsPage();
if (location.pathname.endsWith("/learn-node.html")) await hydrateNodePage();
