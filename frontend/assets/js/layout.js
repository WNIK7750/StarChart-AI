import { apiGet } from "./api.js";

export async function renderNavigation(activeCode) {
  const nav = document.querySelector("[data-nav]");
  if (!nav) return;
  const data = await apiGet("/navigation");
  nav.innerHTML = data.items.map((item) => {
    const active = item.code === activeCode ? "active" : "";
    return `<a class="${active}" href="${item.href}">${item.label}</a>`;
  }).join("");
}

export function bindSpotlight(scope = document) {
  scope.querySelectorAll("[data-spotlight]").forEach((card) => {
    card.addEventListener("mousemove", (event) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${((event.clientX - rect.left) / rect.width) * 100}%`);
      card.style.setProperty("--my", `${((event.clientY - rect.top) / rect.height) * 100}%`);
    });
  });
}
