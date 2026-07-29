import { initHomePage } from "./learning-pages.js";
import { bindNavbarScroll, bindReveal, bindSpotlight, frameThrottle, initPageShell } from "./page-shell.js";

function bindScrollProgress() {
  const bar = document.querySelector("#progressBar");
  if (!bar) return;
  window.addEventListener("scroll", frameThrottle(() => {
    const root = document.documentElement;
    const available = root.scrollHeight - root.clientHeight;
    bar.style.width = `${available > 0 ? (root.scrollTop / available) * 100 : 0}%`;
  }), { passive: true });
}

function bindHeroMotion() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("#heroTitle .word").forEach((word) => word.classList.add("in"));
    return;
  }
  document.querySelectorAll("#heroTitle .word").forEach((word, index) => {
    window.setTimeout(() => word.classList.add("in"), 200 + index * 250);
  });
  const search = document.querySelector("#heroSearch");
  if (!search) return;
  const placeholders = [
    "试试搜索 DeepSeek、ChatGPT、提示工程...",
    "搜索 RAG、Agent、Transformer...",
    "搜索 Kimi、Cursor、Midjourney...",
    "搜索免费 AI 编程助手...",
    "搜索学习路线...",
  ];
  let index = 0;
  window.setInterval(() => {
    if (document.activeElement === search) return;
    index = (index + 1) % placeholders.length;
    search.placeholder = placeholders[index];
  }, 3500);
}

function bindStats() {
  const stats = document.querySelectorAll(".stat-num[data-target]");
  if (!stats.length) return;
  const setValue = (element, value) => {
    if (element.firstChild) element.firstChild.textContent = String(value);
  };
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    stats.forEach((element) => setValue(element, element.dataset.target));
    return;
  }
  stats.forEach((element) => setValue(element, 0));
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const element = entry.target;
      const target = Number.parseInt(element.dataset.target, 10);
      let current = 0;
      const step = Math.max(1, Math.ceil(target / 30));
      const timer = window.setInterval(() => {
        current = Math.min(target, current + step);
        setValue(element, current);
        if (current === target) window.clearInterval(timer);
      }, 40);
      observer.unobserve(element);
    });
  }, { threshold: 0.5 });
  stats.forEach((element) => observer.observe(element));
}

void initPageShell("home").catch((error) => console.warn("Page shell initialization unavailable:", error));
document.querySelector("[data-scroll-top]")?.addEventListener("click", (event) => {
  event.preventDefault();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
bindNavbarScroll();
bindScrollProgress();
bindHeroMotion();
await initHomePage();
bindStats();
bindReveal();
bindSpotlight();
