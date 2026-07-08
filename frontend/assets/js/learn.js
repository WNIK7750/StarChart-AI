import { apiGet } from "./api.js";
import { bindSpotlight, renderNavigation } from "./layout.js";
import { renderRoadmap } from "./roadmap.js";

function resourceCard(item) {
  return `
    <a href="${item.href}" class="resource-card" data-spotlight>
      <div class="resource-cover ${item.coverTheme}">
        <div><small>${item.coverLabel}</small>${item.coverText}</div>
      </div>
      <div class="resource-info">
        <div class="resource-title">${item.title}</div>
        <div class="resource-desc">${item.description}</div>
      </div>
    </a>`;
}

async function renderResources(domain) {
  const grid = document.querySelector("#resourceGrid");
  if (!grid) return;
  const data = await apiGet("/learning/resources", { domain });
  grid.innerHTML = data.items.map(resourceCard).join("");
  bindSpotlight(grid);
}

await renderNavigation("learn");
await renderRoadmap({
  tabsEl: document.querySelector("#domainTabs"),
  canvasEl: document.querySelector("#roadmapCanvas"),
  onDomainChange: renderResources,
});
