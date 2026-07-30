import { initNodePage } from "./learning-pages.js";
import { bindNavbarScroll, bindReveal, initPageShell } from "./page-shell.js";

function bindContentTabs() {
  const tabs = Array.from(document.querySelectorAll(".tab"));
  const activate = (tab) => {
    tabs.forEach((item) => {
      const active = item === tab;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", String(active));
      item.tabIndex = active ? 0 : -1;
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      const active = panel.dataset.panel === tab.dataset.tab;
      panel.hidden = !active;
      if (active) panel.querySelectorAll(".reveal").forEach((element) => element.classList.add("in"));
    });
  };
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => activate(tab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const offset = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(tabs.indexOf(tab) + offset + tabs.length) % tabs.length];
      activate(next);
      next.focus();
    });
  });
}

const shellReady = initPageShell("learn");
void shellReady.catch((error) => console.warn("Page shell initialization unavailable:", error));
bindNavbarScroll();
bindContentTabs();
await initNodePage({ authReady: shellReady.then(([, user]) => user) });
bindReveal();
