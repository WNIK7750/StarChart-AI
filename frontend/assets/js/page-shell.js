import { apiGet } from "./api.js";
import { initAuthUI } from "./auth-ui.js";
import { initSiteSearch } from "./site-search.js";
import { safeInternalHref } from "./url-safety.js";

export const $ = (selector, scope = document) => scope.querySelector(selector);
export const $$ = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

export function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function bindSpotlight(scope = document) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  $$("[data-spotlight]", scope).forEach((card) => {
    if (card.dataset.spotlightBound === "true") return;
    card.dataset.spotlightBound = "true";
    const updateSpotlight = frameThrottle((event) => {
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--mx", `${((event.clientX - rect.left) / rect.width) * 100}%`);
      card.style.setProperty("--my", `${((event.clientY - rect.top) / rect.height) * 100}%`);
    });
    const pointerEvent = "PointerEvent" in window ? "pointermove" : "mousemove";
    card.addEventListener(pointerEvent, updateSpotlight, { passive: true });
  });
}

export function bindReveal(scope = document) {
  const targets = $$(".reveal", scope).filter((element) => element.dataset.revealBound !== "true");
  targets.forEach((element) => { element.dataset.revealBound = "true"; });
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
    targets.forEach((element) => element.classList.add("in"));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: "0px 0px -80px 0px" });
  targets.forEach((element) => observer.observe(element));
}

export function frameThrottle(
  callback,
  schedule = globalThis.requestAnimationFrame?.bind(globalThis)
    || ((run) => globalThis.setTimeout(run, 16)),
) {
  let scheduled = false;
  let latestArgs = [];
  return (...args) => {
    latestArgs = args;
    if (scheduled) return;
    scheduled = true;
    schedule(() => {
      scheduled = false;
      callback(...latestArgs);
    });
  };
}

export function createFrameBuffer(
  render,
  {
    schedule = globalThis.requestAnimationFrame?.bind(globalThis)
      || ((run) => globalThis.setTimeout(run, 16)),
    cancel = globalThis.cancelAnimationFrame?.bind(globalThis)
      || globalThis.clearTimeout?.bind(globalThis),
  } = {},
) {
  let pending = "";
  let frameId = null;
  const renderPending = () => {
    frameId = null;
    if (!pending) return;
    const chunk = pending;
    pending = "";
    render(chunk);
  };
  return {
    push(chunk) {
      pending += String(chunk ?? "");
      if (frameId === null) frameId = schedule(renderPending);
    },
    flush() {
      if (frameId !== null) {
        cancel?.(frameId);
        frameId = null;
      }
      renderPending();
    },
    cancel() {
      if (frameId !== null) cancel?.(frameId);
      frameId = null;
      pending = "";
    },
  };
}

export function bindNavbarScroll(navbar = document.querySelector("#navbar")) {
  if (!navbar || navbar.dataset.scrollBound === "true") return;
  navbar.dataset.scrollBound = "true";
  let lastScroll = window.scrollY;
  window.addEventListener("scroll", frameThrottle(() => {
    const current = window.scrollY;
    navbar.classList.toggle("hidden", current > 80 && current > lastScroll);
    lastScroll = current;
  }), { passive: true });
}

async function hydrateNavigation(activeCode) {
  const navs = $$(".nav-links, .top-nav");
  if (!navs.length) return;
  try {
    const { items } = await apiGet("/navigation");
    const html = items.map((item) => {
      const active = item.code === activeCode ? "active" : "";
      return `<a href="${escapeHtml(safeInternalHref(item.href))}" class="${active}">${escapeHtml(item.label)}</a>`;
    }).join("");
    navs.forEach((nav) => { nav.innerHTML = html; });
  } catch (error) {
    console.warn("Navigation API fallback:", error);
  }
}

export function initPageShell(activeCode) {
  document.addEventListener("click", (event) => {
    if (event.target.closest('a[aria-disabled="true"]')) event.preventDefault();
  });
  initSiteSearch();
  return Promise.all([
    hydrateNavigation(activeCode),
    initAuthUI(),
  ]);
}
