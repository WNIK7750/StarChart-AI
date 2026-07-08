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

await renderNavigation("home");
await renderRoadmap({
  tabsEl: document.querySelector("#domainTabs"),
  canvasEl: document.querySelector("#roadmapCanvas"),
});
const resources = await apiGet("/learning/resources");
document.querySelector("#homeResources").innerHTML = resources.items.slice(0, 3).map(resourceCard).join("");
bindSpotlight();
