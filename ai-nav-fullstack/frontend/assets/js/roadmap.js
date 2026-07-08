import { apiGet } from "./api.js";

function nodeTemplate(node) {
  const current = node.isCurrent ? " current" : "";
  return `
    <g class="km-node${current}" data-node="${node.slug}" transform="translate(${node.x},${node.y})">
      <rect class="km-node-rect" width="${node.width}" height="${node.height}" rx="8"></rect>
      <circle class="km-node-port" cx="0" cy="24" r="4"></circle>
      <circle class="km-node-port" cx="${node.width}" cy="24" r="4"></circle>
      <circle class="km-node-dot" cx="25" cy="24" r="5" fill="${node.color}"></circle>
      <text class="km-node-text" x="42" y="21">${node.title}</text>
      <text class="km-node-sub" x="42" y="36">${node.subtitle}</text>
    </g>`;
}

function legendTemplate(levels) {
  return `<strong>难度</strong>${levels.slice(0, 5).map((item) => `<span><i class="dot" style="background:${item.color}"></i>${item.name}</span>`).join("")}`;
}

export async function renderRoadmap({ tabsEl, canvasEl, onDomainChange } = {}) {
  const data = await apiGet("/learning/roadmap");
  if (tabsEl) {
    tabsEl.innerHTML = data.domains.map((domain, index) => `
      <button class="line-tab ${index === 0 ? "active" : ""}" data-domain="${domain.code}" style="--domain-color:${domain.color};--domain-glow:${domain.glowColor}">
        ${domain.name}
      </button>
    `).join("");
  }
  if (canvasEl) {
    canvasEl.innerHTML = `
      <div class="km-grid-bg"></div>
      <div class="km-legend">${legendTemplate(data.difficultyLevels)}</div>
      <svg class="km-svg" viewBox="${data.viewBox}" xmlns="http://www.w3.org/2000/svg" aria-label="AI 学习路线模块关系图">
        ${data.edges.map((edge) => `<path class="km-link" d="${edge.pathD}"></path>`).join("")}
        ${data.nodes.map(nodeTemplate).join("")}
      </svg>`;
  }

  function applyDomain(domainCode, color, glow) {
    const selected = new Set(data.domainNodes[domainCode] || []);
    canvasEl?.querySelectorAll(".km-node").forEach((node) => {
      node.classList.toggle("domain-selected", selected.has(node.dataset.node));
      node.style.setProperty("--domain-color", color);
      node.style.setProperty("--domain-glow", glow);
    });
    onDomainChange?.(domainCode);
  }

  tabsEl?.querySelectorAll(".line-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      tabsEl.querySelectorAll(".line-tab").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      applyDomain(tab.dataset.domain, tab.style.getPropertyValue("--domain-color"), tab.style.getPropertyValue("--domain-glow"));
    });
  });

  const active = tabsEl?.querySelector(".line-tab.active");
  if (active) applyDomain(active.dataset.domain, active.style.getPropertyValue("--domain-color"), active.style.getPropertyValue("--domain-glow"));
  return data;
}
