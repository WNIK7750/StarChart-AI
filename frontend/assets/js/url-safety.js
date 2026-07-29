import { PUBLIC_BASE_PATH, withPublicBasePath } from "./public-path.js";

const LEGACY_PAGE_PATHS = new Map([
  ["/index.html", "/"],
  ["/assistant.html", "/assistant"],
  ["/learn.html", "/learn"],
  ["/tools.html", "/tools"],
  ["/settings.html", "/settings"],
]);

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
    const canonical = canonicalInternalPath(url.pathname, url.search);
    return `${withPublicBasePath(`${canonical.pathname}${canonical.search}`)}${url.hash}`;
  } catch {
    return fallback;
  }
}

export function canonicalInternalPath(pathname, search = "") {
  const localPath = PUBLIC_BASE_PATH
    && (pathname === PUBLIC_BASE_PATH || pathname.startsWith(`${PUBLIC_BASE_PATH}/`))
    ? pathname.slice(PUBLIC_BASE_PATH.length) || "/"
    : pathname;
  if (localPath === "/learn-node.html") {
    const params = new URLSearchParams(search);
    const slug = params.get("slug") || "";
    params.delete("slug");
    if (/^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$/.test(slug)) {
      const query = params.toString();
      return {
        pathname: `/learn/${encodeURIComponent(slug)}`,
        search: query ? `?${query}` : "",
      };
    }
    return { pathname: "/learn", search: "" };
  }
  return {
    pathname: LEGACY_PAGE_PATHS.get(localPath) || localPath,
    search,
  };
}

export function safeHttpHref(value, fallback = "#") {
  return parseHttpUrl(value)?.href || fallback;
}
