import { withPublicBasePath } from "./public-path.js";

function parseHttpUrl(value) {
  try {
    const url = new URL(String(value || ""), window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url : null;
  } catch {
    return null;
  }
}

export function safeInternalHref(value, fallback = "#") {
  const url = parseHttpUrl(value);
  if (!url || url.origin !== window.location.origin) return fallback;
  try {
    return `${withPublicBasePath(`${url.pathname}${url.search}`)}${url.hash}`;
  } catch {
    return fallback;
  }
}

export function safeHttpHref(value, fallback = "#") {
  return parseHttpUrl(value)?.href || fallback;
}
