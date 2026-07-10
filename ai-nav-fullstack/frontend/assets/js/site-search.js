import { apiGet } from "./api.js";
import "./tool-data.js";

const SEARCH_STYLE_ID = "ai-nav-site-search-style";
let searchIndexPromise = null;

const PAGES = [
  { type: "页面", title: "学习路线", description: "AI 知识地图、学习节点和主资料目录", url: "learn.html#roadmap", keywords: "学习 路线 知识地图 roadmap ai" },
  { type: "页面", title: "工具导航", description: "按场景查找 AI 工具、组合工作流和最新工具", url: "tools.html#directory", keywords: "工具 导航 tools ai workflow 工作流" },
  { type: "页面", title: "AI 学习助手", description: "站内 Agent 问答与工作流生成入口", url: "index.html#assistant", keywords: "助手 agent 工作流 问答" },
  { type: "页面", title: "关于本站", description: "项目定位、内容来源和后续规划", url: "index.html#about", keywords: "关于 项目 说明" },
];

const LEARNING = [
  ["AI 通识", "概念、边界和 AI 基础认知", "learn-node.html?slug=ai-literacy#overview", "ai 人工智能 通识 基础"],
  ["Python", "AI 学习常用语法、环境和实践基础", "learn-node.html?slug=python#overview", "python 编程"],
  ["数学基础", "概率、线代和机器学习前置知识", "learn-node.html?slug=math-foundation#overview", "数学 概率 线性代数"],
  ["机器学习", "监督学习、无监督学习与训练评估", "learn-node.html?slug=machine-learning#overview", "机器学习 ml"],
  ["Transformer", "注意力机制和大模型核心结构", "learn-node.html?slug=transformer#overview", "transformer llm 大模型"],
  ["Prompt", "提示工程、结构化输出和上下文设计", "learn-node.html?slug=prompt#overview", "prompt 提示工程"],
  ["RAG", "检索增强生成、向量库和知识库问答", "learn-node.html?slug=rag#overview", "rag 检索增强 知识库"],
  ["Agent", "规划、工具调用和智能体工作流", "learn-node.html?slug=agent#overview", "agent 智能体 工具调用"],
].map(([title, description, url, keywords]) => ({ type: "学习", title, description, url, keywords }));

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function injectSearchStyles() {
  if (document.getElementById(SEARCH_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = SEARCH_STYLE_ID;
  style.textContent = `
    .site-search-wrap{position:relative;width:clamp(220px,22vw,320px);font-size:13px;line-height:1.35}
    .site-search{height:30px;display:flex;align-items:center;gap:7px;padding:0 9px;border:1px solid #d0d7de;border-radius:7px;background:#fff;box-shadow:inset 0 1px 0 rgba(208,215,222,.2);transition:border-color .16s,box-shadow .16s}
    .site-search:focus-within{border-color:#0969da;box-shadow:0 0 0 3px rgba(9,105,218,.12)}
    .site-search-icon{color:#57606a;font-size:14px;line-height:1}
    .site-search input{min-width:0;flex:1;height:100%;border:0;outline:0;background:transparent;color:#24292f;font:inherit;font-size:13px}
    .site-search input::placeholder{color:#6e7781}
    .site-search kbd{height:20px;min-width:20px;display:grid;place-items:center;border:1px solid #d0d7de;border-radius:5px;background:#f6f8fa;color:#57606a;font-size:12px;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
    .site-search-clear{width:22px;height:22px;display:none;place-items:center;border:0;border-radius:50%;background:#eaeef2;color:#57606a;font-weight:700}
    .site-search.has-value .site-search-clear{display:grid}
    .site-search-popover{position:absolute;left:0;right:0;top:36px;z-index:110;display:none;max-height:min(360px,66vh);overflow:auto;border:1px solid #d0d7de;border-radius:8px;background:#fff;box-shadow:0 12px 28px rgba(31,35,40,.12)}
    .site-search-wrap.open .site-search-popover{display:block}
    .site-result-group{padding:7px 10px 5px;color:#57606a;font-size:12px;font-weight:650;background:#f6f8fa;border-bottom:1px solid #d8dee4}
    .site-result{width:100%;display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:9px;align-items:center;padding:8px 10px;border:0;border-bottom:1px solid #d8dee4;background:#fff;text-align:left;color:#24292f;min-height:52px;overflow:hidden}
    .site-result:last-child{border-bottom:0}.site-result:hover,.site-result.active{background:#f6f8fa}
    .site-result-icon{width:28px;height:28px;border:1px solid #d8dee4;border-radius:7px;background:#fff;display:grid;place-items:center;overflow:hidden;color:#57606a;font-weight:800;font-size:11px;flex:0 0 auto}
    .site-result-icon img{width:20px;height:20px;object-fit:contain}.site-result-title{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .site-result-desc{margin-top:2px;color:#6e7781;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.site-result-type{padding:1px 6px;border-radius:999px;background:#ddf4ff;color:#0969da;font-size:11px;font-weight:650}
    .site-result-arrow{color:#0969da;font-size:16px}.site-result-empty{padding:12px;color:#6e7781;font-size:12px}
    .nav-actions,.top-actions{display:flex;align-items:center;gap:8px}.nav-actions>.icon-btn,.top-actions>.icon-btn,.nav-actions>.btn:not([data-auth-trigger]),.top-actions>.login-btn,.top-actions>.primary-btn{display:none!important}
    @media (max-width:780px){.site-search-wrap{width:44px}.site-search{justify-content:center}.site-search input,.site-search kbd,.site-search-clear{display:none}.site-search-wrap:focus-within,.site-search-wrap.open{width:min(280px,62vw)}.site-search-wrap:focus-within input,.site-search-wrap.open input{display:block}.site-search-wrap:focus-within kbd,.site-search-wrap.open kbd{display:grid}}
  `;
  document.head.appendChild(style);
}

function normalize(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, "");
}

function scoreResult(item, q) {
  const title = normalize(item.title);
  const desc = normalize(item.description);
  const keys = normalize(item.keywords || "");
  if (!q) return item.type === "工具" ? 12 : 8;
  let score = 0;
  if (title === q) score += 100;
  if (title.startsWith(q)) score += 70;
  if (title.includes(q)) score += 52;
  if (keys.includes(q)) score += 34;
  if (desc.includes(q)) score += 18;
  if (score > 0 && item.type === "工具") score += 5;
  return score;
}

async function buildSearchIndex() {
  if (!searchIndexPromise) {
    searchIndexPromise = Promise.allSettled([
      apiGet("/tools", { page_size: 50 }),
      apiGet("/learning/roadmap"),
    ]).then(([toolsResult, roadmapResult]) => {
      const localTools = window.AINavToolData?.tools || [];
      const localCategories = Object.fromEntries((window.AINavToolData?.categories || []).map((cat) => [cat.id, cat]));
      const localPlacements = window.AINavToolData?.placements || [];
      const tools = localTools.length ? localTools.map((tool) => ({
        type: "工具",
        title: tool.name,
        description: `${[...new Set(localPlacements.filter((place) => place.toolId === tool.id).map((place) => localCategories[place.categoryId]?.name).filter(Boolean))].join("、") || "AI 工具"} · ${tool.description}`,
        url: `tools.html?q=${encodeURIComponent(tool.name)}#directory`,
        iconUrl: tool.icon,
        iconFallbacks: tool.iconFallbacks || [],
        mark: tool.mark,
        keywords: `${tool.name} ${(tool.aliases || []).join(" ")} ${tool.description} ${localPlacements.filter((place) => place.toolId === tool.id).map((place) => `${localCategories[place.categoryId]?.name || ""} ${place.subcategory} ${place.tag}`).join(" ")}`,
      })) : toolsResult.status === "fulfilled" ? toolsResult.value.items.map((tool) => ({
        type: "工具",
        title: tool.name,
        description: `${tool.categoryName || "AI 工具"} · ${tool.description}`,
        url: `tools.html?q=${encodeURIComponent(tool.name)}#directory`,
        iconUrl: tool.iconUrl,
        iconFallbacks: tool.iconFallbacks || [],
        mark: tool.mark,
        keywords: `${tool.name} ${tool.description} ${tool.categoryName} ${tool.subcategory} ${tool.tag}`,
      })) : [];
      const nodes = roadmapResult.status === "fulfilled" ? roadmapResult.value.nodes.map((node) => ({
        type: "学习",
        title: node.title,
        description: `${node.subtitle} · 点击查看节点介绍页`,
        url: `learn-node.html?slug=${encodeURIComponent(node.slug)}#overview`,
        keywords: `${node.title} ${node.subtitle} ${node.slug}`,
      })) : LEARNING;
      return [...tools, ...nodes, ...LEARNING, ...PAGES];
    });
  }
  return searchIndexPromise;
}

async function getResults(query) {
  const q = normalize(query);
  const index = await buildSearchIndex();
  return index
    .map((item) => ({ ...item, score: scoreResult(item, q) }))
    .filter((item) => !q || item.score > 0)
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title, "zh-CN"))
    .slice(0, 7);
}

function resultIcon(item) {
  if (item.iconUrl) {
    const fallbackText = escapeHtml(item.mark || item.title.slice(0, 2));
    const fallbacks = escapeHtml(JSON.stringify(item.iconFallbacks || []));
    return `<img src="${escapeHtml(item.iconUrl)}" alt="" loading="lazy" data-fallbacks="${fallbacks}" onerror="const f=JSON.parse(this.dataset.fallbacks||'[]');const n=f.shift();if(n){this.dataset.fallbacks=JSON.stringify(f);this.src=n}else{this.remove();this.parentElement.textContent='${fallbackText}'}">`;
  }
  return escapeHtml(item.mark || item.title.slice(0, 2).toUpperCase());
}

function renderResults(form, results) {
  const popover = form.parentElement.querySelector("[data-search-results]");
  const heading = form.elements.q.value.trim() ? "搜索结果" : "推荐";
  if (!results.length) {
    popover.innerHTML = '<div class="site-result-empty">没有找到匹配结果，试试搜索工具名、学习节点或 Agent。</div>';
    form.parentElement.classList.add("open");
    return;
  }
  popover.innerHTML = `<div class="site-result-group">${heading}</div>` + results.map((item, index) => `
    <button class="site-result ${index === 0 ? "active" : ""}" type="button" data-result-index="${index}">
      <span class="site-result-icon">${resultIcon(item)}</span>
      <span><span class="site-result-title">${escapeHtml(item.title)}<span class="site-result-type">${escapeHtml(item.type)}</span></span><span class="site-result-desc">${escapeHtml(item.description)}</span></span>
      <span class="site-result-arrow">›</span>
    </button>`).join("");
  form._results = results;
  form._activeIndex = 0;
  form.parentElement.classList.add("open");
}

function goToResult(item) {
  if (!item?.url) return;
  window.location.href = new URL(item.url, window.location.href).href;
}

async function updateResults(form) {
  const input = form.elements.q;
  form.classList.toggle("has-value", Boolean(input.value.trim()));
  renderResults(form, await getResults(input.value));
}

function searchFormHtml(value = "") {
  return `
    <div class="site-search-wrap">
      <form class="site-search" data-site-search role="search">
        <span class="site-search-icon">⌕</span>
        <input name="q" type="search" value="${escapeHtml(value)}" placeholder="Type / to search" autocomplete="off">
        <button class="site-search-clear" data-search-clear type="button" aria-label="清空">×</button>
        <kbd>/</kbd>
      </form>
      <div class="site-search-popover" data-search-results></div>
    </div>`;
}

function bindForm(form) {
  const input = form.elements.q;
  input.addEventListener("focus", () => updateResults(form));
  input.addEventListener("input", () => updateResults(form));
  input.addEventListener("keydown", (event) => {
    const results = form._results || [];
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const delta = event.key === "ArrowDown" ? 1 : -1;
      form._activeIndex = (form._activeIndex + delta + results.length) % Math.max(results.length, 1);
      form.parentElement.querySelectorAll(".site-result").forEach((item, index) => item.classList.toggle("active", index === form._activeIndex));
    }
    if (event.key === "Enter") {
      event.preventDefault();
      goToResult(results[form._activeIndex] || results[0]);
    }
    if (event.key === "Escape") form.parentElement.classList.remove("open");
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const results = form._results || [];
    goToResult(results[form._activeIndex] || results[0]);
  });
  form.parentElement.addEventListener("click", (event) => {
    const clear = event.target.closest("[data-search-clear]");
    if (clear) {
      input.value = "";
      input.focus();
      updateResults(form);
      return;
    }
    const result = event.target.closest("[data-result-index]");
    if (result) goToResult((form._results || [])[Number(result.dataset.resultIndex)]);
  });
}

export function initSiteSearch() {
  injectSearchStyles();
  const value = new URLSearchParams(location.search).get("q") || "";
  document.querySelectorAll(".nav-actions, .top-actions").forEach((container) => {
    const oldAuth = container.querySelector("[data-auth-root]");
    container.innerHTML = searchFormHtml(value);
    if (oldAuth) container.appendChild(oldAuth);
  });
  document.querySelectorAll("[data-site-search]").forEach(bindForm);
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      event.preventDefault();
      document.querySelector("[data-site-search] input")?.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".site-search-wrap")) {
      document.querySelectorAll(".site-search-wrap.open").forEach((wrap) => wrap.classList.remove("open"));
    }
  });
  const heroSearch = document.querySelector("#heroSearch");
  if (heroSearch) {
    heroSearch.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        goToResult((await getResults(heroSearch.value))[0]);
      }
    });
  }
  document.querySelectorAll(".hero-tags a").forEach((link) => {
    link.addEventListener("click", async (event) => {
      event.preventDefault();
      goToResult((await getResults(link.textContent))[0]);
    });
  });
  if (value && location.pathname.endsWith("/tools.html")) {
    window.setTimeout(() => {
      const input = document.querySelector("#searchInput, #toolSearch");
      if (input) input.value = value;
      document.querySelector("#searchForm")?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      document.querySelector("#directory")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 250);
  } else if (location.hash) {
    window.setTimeout(() => document.querySelector(location.hash)?.scrollIntoView({ behavior: "smooth", block: "start" }), 180);
  }
}
