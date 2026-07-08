import { apiGet } from "./api.js";
import { bindSpotlight, renderNavigation } from "./layout.js";

const state = { category: "", subcategory: "全部", q: "", freeOnly: false };
const categoryNav = document.querySelector("#categoryNav");
const sections = document.querySelector("#toolsSections");
const searchInput = document.querySelector("#toolSearch");
const freeButton = document.querySelector("#freeOnly");

function faviconUrl(url) {
  try {
    const { hostname } = new URL(url);
    return `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`;
  } catch {
    return "";
  }
}

function brandLogo(tool) {
  const icon = faviconUrl(tool.officialUrl);
  const fallback = `<span class="tool-brand-fallback">${tool.mark}</span>`;
  if (!icon) return fallback;
  return `
    <span class="tool-brand-logo">
      <img src="${icon}" alt="${tool.name} logo" loading="lazy" onerror="this.closest('.tool-brand-logo').outerHTML='${fallback.replace(/'/g, "&#39;")}'">
    </span>`;
}

function toolCard(tool) {
  return `
    <a class="tool-card" href="${tool.officialUrl}" target="_blank" data-spotlight>
      ${brandLogo(tool)}
      <div class="tool-info"><strong>${tool.name}</strong><p>${tool.description}</p></div>
      <div class="tool-meta"><span class="tag">${tool.subcategory}</span><span>›</span></div>
    </a>`;
}

function latestCard(tool) {
  return `
    <a class="latest-card" href="${tool.officialUrl}" target="_blank">
      ${brandLogo(tool)}
      <div class="resource-info">
        <div class="resource-title">${tool.name}</div>
        <div class="resource-desc">${tool.description}</div>
      </div>
    </a>`;
}

function workflowCard(workflow) {
  const chain = workflow.tools.map((tool, index) => `
    ${index ? '<span class="chain-arrow"></span>' : ''}
    <span class="tool-item"><span class="tool-icon">${tool.mark}</span>${tool.name}</span>
  `).join("");
  return `
    <article class="workflow-card">
      <div class="workflow-card__top"><span class="popular-badge">${workflow.badge}</span><span class="trend-icon">↗</span></div>
      <h2>${workflow.title}</h2>
      <p>${workflow.description}</p>
      <div class="tool-chain">${chain}</div>
    </article>`;
}

function subTabs(category) {
  return `<div class="section-subnav">${category.subcategories.map((sub) => `
    <button class="${state.category === category.code && state.subcategory === sub ? "active" : ""}" data-sub="${sub}" data-cat="${category.code}">${sub}</button>
  `).join("")}</div>`;
}

async function renderCategories(categories) {
  categoryNav.innerHTML = categories.map((category) => `
    <button class="rail-link ${state.category === category.code ? "active" : ""}" data-cat="${category.code}">
      <span>${category.icon}</span>${category.name}
    </button>`).join("");
  categoryNav.querySelectorAll("[data-cat]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.category = btn.dataset.cat;
      state.subcategory = "全部";
      renderTools(categories);
    });
  });
}

async function renderTools(categories) {
  await renderCategories(categories);
  const visibleCategories = state.category ? categories.filter((item) => item.code === state.category) : categories;
  const html = await Promise.all(visibleCategories.map(async (category) => {
    const data = await apiGet("/tools", {
      category: category.code,
      subcategory: state.category === category.code ? state.subcategory : "全部",
      q: state.q,
      free_only: state.freeOnly,
      page_size: 12,
    });
    if (!data.items.length) return "";
    return `
      <section class="category-section panel" id="section-${category.code}">
        <div class="section-head">
          <div><h2>${category.name}</h2><p>${category.description}</p></div>
          <p>${data.total} 个工具</p>
        </div>
        ${subTabs(category)}
        <div class="tools-grid">${data.items.map(toolCard).join("")}</div>
      </section>`;
  }));
  sections.innerHTML = html.join("") || `<div class="panel category-section">没有找到匹配工具，换个关键词试试。</div>`;
  sections.querySelectorAll("[data-sub]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.category = btn.dataset.cat;
      state.subcategory = btn.dataset.sub;
      renderTools(categories);
    });
  });
  bindSpotlight(sections);
}

await renderNavigation("tools");
const categoryData = await apiGet("/tools/categories");
const categories = categoryData.items;
await renderTools(categories);

document.querySelector("#searchForm")?.addEventListener("submit", (event) => {
  event.preventDefault();
  state.q = searchInput.value.trim();
  renderTools(categories);
});
searchInput.addEventListener("input", () => {
  state.q = searchInput.value.trim();
  renderTools(categories);
});
freeButton.addEventListener("click", () => {
  state.freeOnly = !state.freeOnly;
  freeButton.classList.toggle("active", state.freeOnly);
  renderTools(categories);
});
document.querySelectorAll("[data-query]").forEach((btn) => {
  btn.addEventListener("click", () => {
    searchInput.value = btn.dataset.query;
    state.q = btn.dataset.query;
    renderTools(categories);
    document.querySelector("#directory")?.scrollIntoView({ behavior: "smooth" });
  });
});
document.querySelectorAll("[data-hot='free']").forEach((btn) => {
  btn.addEventListener("click", () => freeButton.click());
});
document.querySelectorAll("[data-scroll]").forEach((btn) => {
  btn.addEventListener("click", () => document.querySelector(`#${btn.dataset.scroll}`)?.scrollIntoView({ behavior: "smooth" }));
});
document.querySelector("#railToggle")?.addEventListener("click", () => {
  document.querySelector(".page-shell")?.classList.toggle("rail-collapsed");
});
window.addEventListener("scroll", () => {
  const h = document.documentElement;
  const progress = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
  document.querySelector("#progressBar").style.width = `${progress * 100}%`;
}, { passive: true });

const latest = await apiGet("/tools/latest");
document.querySelector("#latestTools").innerHTML = latest.items.map(latestCard).join("");

const workflows = await apiGet("/tools/workflows");
document.querySelector("#workflowGrid").innerHTML = workflows.items.map(workflowCard).join("");
