const PUBLIC_PATH_MODULE_SUFFIX = "/assets/js/public-path.js";

function publicPathError(message) {
  return new TypeError(`Invalid public path: ${message}`);
}

function validatePathname(pathname) {
  if (/%(?:2f|5c)/i.test(pathname)) {
    throw publicPathError("encoded path separators are not allowed");
  }
  if (
    !pathname.startsWith("/")
    || pathname.startsWith("//")
    || pathname.includes("\\")
    || pathname.includes("//")
  ) {
    throw publicPathError("expected one root-relative browser path");
  }
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    throw publicPathError("malformed percent encoding");
  }
  if (decoded.includes("\\") || decoded.includes("//")) {
    throw publicPathError("encoded path separators are not allowed");
  }
  if (decoded.split("/").some((part) => part === "." || part === "..")) {
    throw publicPathError("path traversal is not allowed");
  }
}

export function normalizePublicBasePath(value) {
  if (typeof value !== "string") {
    throw publicPathError("base path must be a string");
  }
  const normalized = value.trim();
  if (!normalized || normalized === "/") return "";
  if (
    normalized.includes("?")
    || normalized.includes("#")
    || /^[a-z][a-z\d+.-]*:/i.test(normalized)
  ) {
    throw publicPathError("base path must not be an absolute URL");
  }
  validatePathname(normalized);
  const withoutTrailingSlash = normalized.endsWith("/")
    ? normalized.slice(0, -1)
    : normalized;
  return withoutTrailingSlash;
}

export function detectPublicBasePath(moduleUrl = import.meta.url) {
  if (
    typeof window !== "undefined"
    && Object.prototype.hasOwnProperty.call(window, "AI_NAV_PUBLIC_BASE_PATH")
  ) {
    return normalizePublicBasePath(window.AI_NAV_PUBLIC_BASE_PATH);
  }
  let modulePath;
  try {
    modulePath = new URL(moduleUrl).pathname;
  } catch {
    throw publicPathError("module URL is invalid");
  }
  if (!modulePath.endsWith(PUBLIC_PATH_MODULE_SUFFIX)) {
    throw publicPathError("module URL does not identify public-path.js");
  }
  return normalizePublicBasePath(
    modulePath.slice(0, -PUBLIC_PATH_MODULE_SUFFIX.length),
  );
}

export function withPublicBasePath(path, basePath = PUBLIC_BASE_PATH) {
  if (typeof path !== "string" || !path) {
    throw publicPathError("browser path must be a non-empty string");
  }
  if (/^[a-z][a-z\d+.-]*:/i.test(path) || path.includes("#")) {
    throw publicPathError("absolute URLs and fragments are not allowed");
  }
  const queryIndex = path.indexOf("?");
  const pathname = queryIndex === -1 ? path : path.slice(0, queryIndex);
  const query = queryIndex === -1 ? "" : path.slice(queryIndex);
  validatePathname(pathname);

  const canonicalBase = normalizePublicBasePath(basePath);
  if (!canonicalBase) return `${pathname}${query}`;

  if (pathname === canonicalBase || pathname.startsWith(`${canonicalBase}/`)) {
    const remainder = pathname.slice(canonicalBase.length);
    if (remainder === canonicalBase || remainder.startsWith(`${canonicalBase}/`)) {
      throw publicPathError("deployment prefix must not be repeated");
    }
    return `${pathname}${query}`;
  }
  return `${canonicalBase}${pathname}${query}`;
}

export const PUBLIC_BASE_PATH = detectPublicBasePath();
export const API_BASE = `${PUBLIC_BASE_PATH}/api/v1`;
