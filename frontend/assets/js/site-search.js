import { apiGet } from "./api.js";
import { safeHttpHref, safeInternalHref } from "./url-safety.js";

const SEARCH_STYLE_ID = "ai-nav-site-search-style";
const SEARCH_DEBOUNCE_MS = 180;
let searchIndexPromise = null;

const PAGES = [
  { type: "页面", title: "学习路线", description: "AI 知识地图、学习节点和主资料目录。", url: "learn.html#roadmap", keywords: "学习 路线 知识地图 roadmap ai 课程 节点" },
  { type: "页面", title: "工具导航", description: "按场景查找 AI 工具、组合工作流和最新工具。", url: "tools.html#directory", keywords: "工具 导航 tools ai workflow 工作流 推荐" },
  { type: "页面", title: "AI 学习助手", description: "站内 Agent 问答与工作流生成入口。", url: "assistant.html", keywords: "助手 agent 工作流 问答 智能体" },
  { type: "页面", title: "关于本站", description: "项目定位、内容来源和后续规划。", url: "index.html#about", keywords: "关于 项目 说明" },
];

const LEARNING = [
  ["AI 通识", "概念、边界和 AI 基础认知。", "learn-node.html?slug=ai-literacy#overview", "ai 人工智能 通识 基础"],
  ["Python", "AI 学习常用语法、环境和实践基础。", "learn-node.html?slug=python#overview", "python 编程"],
  ["数学基础", "概率、线代和机器学习前置知识。", "learn-node.html?slug=math-foundation#overview", "数学 概率 线性代数"],
  ["机器学习", "监督学习、无监督学习与训练评估。", "learn-node.html?slug=machine-learning#overview", "机器学习 ml"],
  ["Transformer", "注意力机制和大模型核心结构。", "learn-node.html?slug=transformer#overview", "transformer llm 大模型"],
  ["Prompt", "提示工程、结构化输出和上下文设计。", "learn-node.html?slug=prompt#overview", "prompt 提示工程"],
  ["RAG", "检索增强生成、向量库和知识库问答。", "learn-node.html?slug=rag#overview", "rag 检索增强 知识库"],
  ["Agent", "规划、工具调用和智能体工作流。", "learn-node.html?slug=agent#overview", "agent 智能体 工具调用"],
].map(([title, description, url, keywords]) => ({ type: "学习", title, description, url, keywords }));

const QUERY_EXPANSIONS = {
  企业: "企业 公司 团队 商业化 安全 隐私 合规 私有化 权限 协作 enterprise business security privacy compliance copilot tabnine sentry glean notion",
  企业级: "企业 公司 团队 商业化 安全 隐私 合规 私有化 权限 协作 enterprise business security privacy compliance copilot tabnine sentry glean notion",
  公司: "企业 团队 协作 办公 安全 权限",
  团队: "企业 协作 办公 会议 文档 工作流",
  安全: "隐私 合规 权限 代码审查 测试 运维 sentry snyk",
  私有化: "企业 安全 隐私 本地 部署",
  代码: "编程 开发 ide copilot cursor code tabnine claude code",
  编程: "代码 开发 ide copilot cursor code tabnine",
  写作: "文本 文案 论文 公文 翻译",
  画图: "绘画 图像 设计 生图 修图",
  视频: "剪辑 数字人 文生视频 配音 音乐",
  搜索: "检索 研究 资料 问答 数据",
  论文: "研究 学术 文献 引用 阅读",
  阅读: "论文 文献 资料 pdf 文档 总结 问答 notebooklm chatdoc chatpdf",
  自动化: "工作流 办公 连接器 zapier make",
  工作流: "workflow agent 自动化 工具组合",
  国产: "国内 中文 中国 内网 大模型",
};

const PINYIN_ALIASES = {
  doubao: "豆包 字节跳动",
  tongyi: "通义 千问 万相 灵码 阿里",
  wenxin: "文心 百度 一言 一格",
  kimi: "月之暗面 长文本",
  yuanbao: "腾讯 元宝",
  deepseek: "深度求索 国产 大模型",
  jianying: "剪映 capcut",
  jimeng: "即梦 字节跳动",
  kling: "可灵 快手",
  quark: "夸克 阿里 搜索 ppt",
  metaso: "秘塔 搜索",
};

const RECOMMENDED_TOOL_NAMES = [
  "ChatGPT",
  "DeepSeek",
  "Claude",
  "豆包",
  "Cursor",
  "Google NotebookLM",
  "Perplexity",
];

const INTENT_TOOL_BOOSTS = [
  { match: /code|代码|编程|开发|ide/i, names: ["Cursor", "GitHub Copilot", "Claude Code", "Tabnine", "CodeBuddy", "Codeium", "通义灵码", "Trae"] },
  { match: /企业|公司|团队|商业|enterprise|安全|合规|私有/i, names: ["Tabnine", "Glean", "钉钉 AI 助理", "Microsoft Copilot", "Notion AI", "GitHub Copilot", "Sentry", "Snyk AI"] },
  { match: /论文|学术|研究|文献/i, names: ["Google NotebookLM", "Perplexity", "Consensus", "Elicit", "Scite", "ChatDOC"] },
  { match: /自动化|工作流|workflow/i, names: ["Zapier AI", "Make", "Coze 扣子", "Gumloop", "Flowith"] },
];

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
    .site-search-popover{position:absolute;left:0;right:0;top:36px;z-index:110;display:none;max-height:min(380px,66vh);overflow:auto;border:1px solid #d0d7de;border-radius:8px;background:#fff;box-shadow:0 12px 28px rgba(31,35,40,.12)}
    .site-search-wrap.open .site-search-popover{display:block}
    .site-result-group{padding:7px 10px 5px;color:#57606a;font-size:12px;font-weight:650;background:#f6f8fa;border-bottom:1px solid #d8dee4}
    .site-result{width:100%;display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:9px;align-items:center;padding:8px 10px;border:0;border-bottom:1px solid #d8dee4;background:#fff;text-align:left;color:#24292f;min-height:52px;overflow:hidden}
    .site-result:last-child{border-bottom:0}.site-result:hover,.site-result.active{background:#f6f8fa}
    .site-result-icon{width:28px;height:28px;border:1px solid #d8dee4;border-radius:7px;background:#fff;display:grid;place-items:center;overflow:hidden;color:#57606a;font-weight:800;font-size:11px;flex:0 0 auto}
    .site-result-icon img{width:20px;height:20px;object-fit:contain}.site-result-title{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .site-result-desc{margin-top:2px;color:#6e7781;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.site-result-type{padding:1px 6px;border-radius:999px;background:#ddf4ff;color:#0969da;font-size:11px;font-weight:650}
    .site-result-reason{padding:1px 6px;border-radius:999px;background:#f6f8fa;color:#57606a;font-size:11px;font-weight:600}
    .site-result-arrow{color:#0969da;font-size:16px}.site-result-empty{padding:12px;color:#6e7781;font-size:12px}
    .nav-actions,.top-actions{display:flex;align-items:center;gap:8px}.nav-actions>.icon-btn,.top-actions>.icon-btn,.nav-actions>.btn:not([data-auth-trigger]),.top-actions>.login-btn,.top-actions>.primary-btn{display:none!important}
    @media (max-width:780px){.site-search-wrap{width:44px}.site-search{justify-content:center}.site-search input,.site-search kbd,.site-search-clear{display:none}.site-search-wrap:focus-within,.site-search-wrap.open{width:min(280px,62vw)}.site-search-wrap:focus-within input,.site-search-wrap.open input{display:block}.site-search-wrap:focus-within kbd,.site-search-wrap.open kbd{display:grid}}
  `;
  document.head.appendChild(style);
}

function compact(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, "");
}

function terms(value) {
  const raw = String(value || "").toLowerCase();
  const latin = raw.match(/[a-z0-9.+#-]+/g) || [];
  const cjk = raw.match(/[\u4e00-\u9fa5]{1,}/g) || [];
  const cjkTerms = cjk.flatMap((word) => {
    if (word.length <= 2) return [word];
    const grams = [word];
    for (let i = 0; i < word.length - 1; i += 1) grams.push(word.slice(i, i + 2));
    return grams;
  });
  return [...new Set([...latin, ...cjkTerms].filter((term) => term.length > 0))];
}

function expandQuery(query) {
  const raw = String(query || "").trim().toLowerCase();
  const baseTerms = terms(raw);
  const extra = [];
  const knownKeys = [...Object.keys(QUERY_EXPANSIONS).map((key) => key.toLowerCase()), ...Object.keys(PINYIN_ALIASES), "code", "ide", "agent", "workflow", "rag", "prompt", "llm", "ppt", "pdf"]
    .sort((a, b) => b.length - a.length);
  let remainder = raw;
  knownKeys.forEach((key) => {
    remainder = remainder.replaceAll(key, "");
  });
  Object.entries(QUERY_EXPANSIONS).forEach(([key, value]) => {
    if (raw.includes(key) || baseTerms.includes(key)) extra.push(value);
  });
  Object.entries(PINYIN_ALIASES).forEach(([key, value]) => {
    if (raw.includes(key)) extra.push(value);
  });
  return {
    raw,
    compact: compact(raw),
    terms: [...new Set([...baseTerms, ...terms(extra.join(" "))])],
    directTerms: baseTerms,
    isKnownIntent: Object.keys(QUERY_EXPANSIONS).some((key) => raw === key.toLowerCase())
      || Object.keys(PINYIN_ALIASES).some((key) => raw === key)
      || /^(code|ide|agent|workflow|rag|prompt|llm|ppt|pdf)$/i.test(raw)
      || (raw.length > 0 && remainder.length === 0),
  };
}

function includesAny(text, values) {
  return values.some((value) => text.includes(value));
}

function enrichItem(item) {
  const title = compact(item.title);
  const description = compact(item.description);
  const keywords = compact(item.keywords);
  const allText = compact(`${item.title} ${item.description} ${item.keywords}`);
  const termSet = terms(`${item.title} ${item.description} ${item.keywords}`).join(" ");
  return { ...item, _title: title, _description: description, _keywords: keywords, _allText: allText, _termText: termSet };
}

async function buildSearchIndex() {
  if (!searchIndexPromise) {
    const requests = [apiGet("/tools/catalog"), apiGet("/learning/roadmap")];
    searchIndexPromise = Promise.allSettled(requests).then(([toolsResult, roadmapResult]) => {
      const apiTools = toolsResult.status === "fulfilled" ? toolsResult.value.tools.map((tool) => ({
        type: "工具",
        title: tool.name,
        description: `${tool.categories?.join("、") || "AI 工具"} · ${tool.description}`,
        url: `tools.html?q=${encodeURIComponent(tool.name)}#directory`,
        iconUrl: tool.icon,
        iconFallbacks: tool.iconFallbacks || [],
        mark: tool.mark,
        heat: tool.heat || 0,
        source: "tool",
        keywords: `${tool.name} ${(tool.aliases || []).join(" ")} ${tool.description} ${(tool.categories || []).join(" ")} ${(tool.subcategories || []).join(" ")} ${(tool.tags || []).join(" ")}`,
      })) : [];
      const nodes = roadmapResult.status === "fulfilled" ? roadmapResult.value.nodes.map((node) => ({
        type: "学习",
        title: node.title,
        description: `${node.subtitle} · 点击查看节点介绍页。`,
        url: `learn-node.html?slug=${encodeURIComponent(node.slug)}#overview`,
        keywords: `${node.title} ${node.subtitle} ${node.slug}`,
      })) : LEARNING;
      return [...apiTools, ...nodes, ...PAGES].map(enrichItem);
    });
  }
  return searchIndexPromise;
}

function reasonFor(item, query) {
  if (!query.raw) return item.source === "tool" ? "推荐" : "入口";
  if (item._title === query.compact) return "精确匹配";
  if (item._title.startsWith(query.compact)) return "名称前缀";
  if (includesAny(item._keywords, query.directTerms.map(compact))) return "关键词";
  if (includesAny(item._description, query.directTerms.map(compact))) return "描述相关";
  return "相关推荐";
}

function meaningfulDirectTerms(query) {
  return query.directTerms
    .map(compact)
    .filter((term) => term.length >= 2)
    .filter((term) => !/^[的了呢吗啊吧和与及或在是有用找搜查看我要想做个一个一种什么如何怎么]$/.test(term))
    .filter((term) => term !== query.compact || term.length <= 5);
}

function directMatchCount(item, query) {
  return meaningfulDirectTerms(query)
    .filter((term) => item._title.includes(term) || item._keywords.includes(term) || item._description.includes(term))
    .length;
}

function isAcceptableMatch(item, query) {
  if (!query.raw) return true;
  if (item.score <= 18) return false;
  if (query.isKnownIntent) return true;
  const direct = meaningfulDirectTerms(query);
  if (!direct.length) return item.score >= 80;
  const matched = item.directMatches || 0;
  if (direct.length <= 2) return matched >= 1;
  return matched >= Math.min(2, Math.ceil(direct.length * 0.45));
}

function scoreResult(item, query) {
  if (!query.raw) {
    const recommendedIndex = RECOMMENDED_TOOL_NAMES.indexOf(item.title);
    if (recommendedIndex >= 0) return 120 - recommendedIndex;
    return (item.source === "tool" ? 48 : 30) + (item.heat || 0) / 8;
  }

  const q = query.compact;
  const direct = query.directTerms.map(compact);
  let score = 0;
  if (item._title === q) score += 260;
  if (item._title.startsWith(q)) score += 180;
  if (item._title.includes(q)) score += 135;
  if (item._keywords.includes(q)) score += 90;
  if (item._description.includes(q)) score += 45;

  query.terms.forEach((term) => {
    const t = compact(term);
    if (!t) return;
    const directWeight = direct.includes(t) ? 1 : 0.42;
    if (item._title.includes(t)) score += 38 * directWeight;
    if (item._keywords.includes(t)) score += 22 * directWeight;
    if (item._description.includes(t)) score += 12 * directWeight;
    if (item._termText.includes(t)) score += 8 * directWeight;
  });

  if (score > 0 && item.source === "tool") score += 6 + Math.min(18, (item.heat || 0) / 6);
  if (query.raw.includes("企业") && item.source === "tool" && /安全|隐私|团队|协作|办公|代码|enterprise|business|sentry|tabnine|copilot|glean|notion/i.test(item.keywords)) score += 58;
  if (query.raw.includes("国产") && /国产|国内|中文|中国|阿里|百度|腾讯|字节|月之暗面|深度求索/i.test(item.keywords)) score += 70;
  INTENT_TOOL_BOOSTS.forEach((intent) => {
    const index = intent.names.indexOf(item.title);
    if (index >= 0 && intent.match.test(query.raw)) score += 90 - index * 5;
  });
  return score;
}

async function getResults(queryText, limit = 7, signal) {
  try {
    const data = await apiGet("/tools/search", { q: queryText || "", limit }, { retryCount: 0, signal });
    if (Array.isArray(data.items)) return data.items.map((item) => ({
      type: item.type,
      title: item.title,
      description: item.description,
      url: item.href,
      iconUrl: item.iconUrl,
      iconFallbacks: item.iconFallbacks || [],
      mark: item.mark,
      score: item.score,
      reason: item.reason,
      source: "api",
    }));
  } catch (error) {
    if (signal?.aborted) throw error;
    // Local catalog fallback keeps static previews usable when the API is not running.
  }
  const query = expandQuery(queryText);
  const index = await buildSearchIndex();
  return index
    .map((item) => {
      const score = scoreResult(item, query);
      const scored = { ...item, score, directMatches: directMatchCount(item, query) };
      return { ...scored, reason: reasonFor(scored, query) };
    })
    .filter((item) => isAcceptableMatch(item, query))
    .sort((a, b) => b.score - a.score || (b.heat || 0) - (a.heat || 0) || a.title.localeCompare(b.title, "zh-CN"))
    .slice(0, limit);
}

function resultIcon(item) {
  if (item.iconUrl) {
    const fallbackText = escapeHtml(item.mark || item.title.slice(0, 2));
    const fallbacks = escapeHtml(JSON.stringify((item.iconFallbacks || [])
      .map((value) => safeHttpHref(value, ""))
      .filter(Boolean)));
    return `<img src="${escapeHtml(safeHttpHref(item.iconUrl))}" alt="" loading="lazy" data-fallbacks="${fallbacks}" onerror="const f=JSON.parse(this.dataset.fallbacks||'[]');const n=f.shift();if(n){this.dataset.fallbacks=JSON.stringify(f);this.src=n}else{this.remove();this.parentElement.textContent='${fallbackText}'}">`;
  }
  return escapeHtml(item.mark || item.title.slice(0, 2).toUpperCase());
}

function renderResults(form, results) {
  const popover = form.parentElement.querySelector("[data-search-results]");
  const heading = form.elements.q.value.trim() ? "搜索结果" : "推荐";
  if (!results.length) {
    popover.innerHTML = '<div class="site-result-empty">没有找到匹配结果，可以试试工具名、分类、用途或学习节点。</div>';
    form.parentElement.classList.add("open");
    return;
  }
  popover.innerHTML = `<div class="site-result-group">${heading}</div>` + results.map((item, index) => `
    <button class="site-result ${index === 0 ? "active" : ""}" type="button" data-result-index="${index}">
      <span class="site-result-icon">${resultIcon(item)}</span>
      <span>
        <span class="site-result-title">${escapeHtml(item.title)}<span class="site-result-type">${escapeHtml(item.type)}</span><span class="site-result-reason">${escapeHtml(item.reason)}</span></span>
        <span class="site-result-desc">${escapeHtml(item.description)}</span>
      </span>
      <span class="site-result-arrow">›</span>
    </button>`).join("");
  form._results = results;
  form._activeIndex = 0;
  form.parentElement.classList.add("open");
}

function goToResult(item) {
  if (!item?.url) return;
  const href = safeInternalHref(item.url, "");
  if (href) window.location.href = href;
}

async function updateResults(form, { signal, sequence } = {}) {
  const input = form.elements.q;
  form.classList.toggle("has-value", Boolean(input.value.trim()));
  const results = await getResults(input.value, 7, signal);
  if (sequence !== undefined && sequence !== form._searchSequence) return;
  renderResults(form, results);
}

function requestResults(form, { debounce = false } = {}) {
  const input = form.elements.q;
  form._searchSequence = (form._searchSequence || 0) + 1;
  const sequence = form._searchSequence;
  if (form._searchTimer) window.clearTimeout(form._searchTimer);
  form._searchTimer = null;
  form._searchController?.abort();

  const run = () => {
    form._searchTimer = null;
    const controller = new AbortController();
    form._searchController = controller;
    updateResults(form, { signal: controller.signal, sequence }).catch((error) => {
      if (controller.signal.aborted || sequence !== form._searchSequence) return;
      console.warn("Site search unavailable:", error);
    });
  };

  if (debounce && input.value.trim()) {
    form._searchTimer = window.setTimeout(run, SEARCH_DEBOUNCE_MS);
    return;
  }
  run();
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

function setActiveResult(form) {
  form.parentElement.querySelectorAll(".site-result").forEach((item, index) => {
    item.classList.toggle("active", index === form._activeIndex);
  });
}

function bindForm(form) {
  const input = form.elements.q;
  input.addEventListener("focus", () => requestResults(form));
  input.addEventListener("input", () => requestResults(form, { debounce: true }));
  input.addEventListener("keydown", (event) => {
    const results = form._results || [];
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const delta = event.key === "ArrowDown" ? 1 : -1;
      form._activeIndex = (form._activeIndex + delta + results.length) % Math.max(results.length, 1);
      setActiveResult(form);
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
      requestResults(form);
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
  if (location.hash && !location.pathname.endsWith("/tools.html")) {
    window.setTimeout(() => document.querySelector(location.hash)?.scrollIntoView({ behavior: "smooth", block: "start" }), 180);
  }
}
