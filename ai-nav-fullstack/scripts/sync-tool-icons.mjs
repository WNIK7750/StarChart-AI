import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataPath = path.join(root, "frontend/assets/js/tool-data.js");
const iconDir = path.join(root, "frontend/assets/icons/tools");

function loadToolData() {
  const sandbox = { window: {} };
  vm.runInNewContext(fs.readFileSync(dataPath, "utf8"), sandbox, { filename: dataPath });
  return sandbox.window.AINavToolData;
}

function saveToolData(data) {
  const source = `// Tool facts: one canonical record per tool; category display entries live in placements.\n(function () {\n  window.AINavToolData = ${JSON.stringify(data, null, 2)};\n\n  window.AINavFindTool = function findTool(name) {\n    const value = String(name || '').trim();\n    return window.AINavToolData.tools.find((tool) => tool.name === value || tool.aliases.includes(value) || tool.id === value) || null;\n  };\n})();\n`;
  fs.writeFileSync(dataPath, source, "utf8");
}

function colorFor(text) {
  let hash = 0;
  for (const char of text) hash = (hash * 31 + char.codePointAt(0)) >>> 0;
  const hues = [210, 185, 258, 199, 222, 16, 278, 148, 232, 336];
  return hues[hash % hues.length];
}

function fallbackSvg(tool) {
  const hue = colorFor(tool.id);
  const mark = String(tool.mark || tool.name.slice(0, 2)).replace(/[&<>]/g, "");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="hsl(${hue} 78% 48%)"/><stop offset="1" stop-color="hsl(${(hue + 52) % 360} 88% 56%)"/></linearGradient></defs><rect width="96" height="96" rx="24" fill="url(#g)"/><text x="48" y="57" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="800" fill="white">${mark}</text></svg>`;
}

function readTextIfSmall(file) {
  if (!fs.existsSync(file)) return "";
  const stat = fs.statSync(file);
  if (stat.size > 256 * 1024) return "";
  return fs.readFileSync(file, "utf8");
}

function isGeneratedPlaceholder(file) {
  const text = readTextIfSmall(file);
  return /<svg\b/i.test(text) && /<linearGradient\b/i.test(text) && /<text\b/i.test(text);
}

function isBadIcon(file) {
  if (!fs.existsSync(file)) return true;
  const head = fs.readFileSync(file).subarray(0, 160).toString("utf8").trim().toLowerCase();
  return head.startsWith("<!doctype html") || head.startsWith("<html") || head.includes("<html");
}

function hostFrom(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return "";
  }
}

function originFrom(url) {
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

function officialCandidates(tool) {
  const fallbacks = tool.iconFallbacks || [];
  const origin = originFrom(tool.url);
  const host = hostFrom(tool.url);
  const encodedHost = encodeURIComponent(host);
  const candidates = [
    ...fallbacks.filter((url) => url.includes("cdn.simpleicons.org")),
    ...(origin ? [`${origin}/favicon.svg`, `${origin}/favicon.ico`] : []),
    ...fallbacks.filter((url) => !url.includes("icons.duckduckgo.com") && !url.includes("cdn.simpleicons.org")),
    ...(host ? [`https://icons.duckduckgo.com/ip3/${host}.ico`] : []),
    ...fallbacks.filter((url) => url.includes("icons.duckduckgo.com")),
    ...(host ? [
      `https://www.google.com/s2/favicons?domain=${encodedHost}&sz=128`,
      `https://www.google.com/s2/favicons?domain_url=${encodedHost}&sz=128`,
      `https://favicon.im/${host}?larger=true`,
    ] : []),
  ];
  return [...new Set(candidates.filter(Boolean))];
}

function extensionFor(response, buffer, url) {
  const type = (response.headers.get("content-type") || "").toLowerCase();
  const head = buffer.subarray(0, 160).toString("utf8").trim().toLowerCase();
  if (type.includes("svg") || head.startsWith("<svg")) return ".svg";
  if (type.includes("png")) return ".png";
  if (type.includes("webp")) return ".webp";
  if (type.includes("jpeg") || type.includes("jpg")) return ".jpg";
  if (type.includes("icon") || type.includes("x-icon") || type.includes("vnd.microsoft.icon")) return ".ico";
  const pathname = (() => {
    try {
      return new URL(url).pathname.toLowerCase();
    } catch {
      return "";
    }
  })();
  if (pathname.endsWith(".svg")) return ".svg";
  if (pathname.endsWith(".png")) return ".png";
  if (pathname.endsWith(".webp")) return ".webp";
  if (pathname.endsWith(".jpg") || pathname.endsWith(".jpeg")) return ".jpg";
  if (pathname.endsWith(".ico")) return ".ico";
  return ".ico";
}

function isHtml(buffer) {
  const head = buffer.subarray(0, 240).toString("utf8").trim().toLowerCase();
  return head.startsWith("<!doctype html") || head.startsWith("<html") || head.includes("<html");
}

async function fetchIcon(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(url, {
      redirect: "follow",
      signal: controller.signal,
      headers: {
        "user-agent": "Mozilla/5.0 AI-Nav icon sync",
        "accept": "image/avif,image/webp,image/png,image/svg+xml,image/x-icon,image/*,*/*;q=0.8",
      },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const buffer = Buffer.from(await response.arrayBuffer());
    if (!buffer.length || isHtml(buffer)) throw new Error("not an image");
    return { buffer, ext: extensionFor(response, buffer, url) };
  } finally {
    clearTimeout(timer);
  }
}

async function replaceWithOfficialIcon(tool) {
  const errors = [];
  for (const url of officialCandidates(tool)) {
    try {
      const { buffer, ext } = await fetchIcon(url);
      const next = path.join(iconDir, `${tool.id}${ext}`);
      fs.writeFileSync(next, buffer);
      tool.icon = `assets/icons/tools/${tool.id}${ext}`;
      return { ok: true, source: url, icon: tool.icon };
    } catch (error) {
      errors.push(`${url}: ${error.message}`);
    }
  }
  return { ok: false, errors };
}

const data = loadToolData();
fs.mkdirSync(iconDir, { recursive: true });

const refreshAll = process.argv.includes("--refresh") || process.argv.includes("--all");
let generated = 0;
let downloaded = 0;
const failed = [];
const targets = data.tools.filter((tool) => {
  const current = path.join(root, "frontend", tool.icon);
  return refreshAll || isBadIcon(current) || isGeneratedPlaceholder(current);
});

async function mapLimit(items, limit, worker) {
  const results = [];
  const executing = new Set();
  for (const item of items) {
    const promise = Promise.resolve().then(() => worker(item));
    results.push(promise);
    executing.add(promise);
    promise.finally(() => executing.delete(promise));
    if (executing.size >= limit) await Promise.race(executing);
  }
  return Promise.all(results);
}

console.log(JSON.stringify({ totalTargets: targets.length }));
const results = await mapLimit(targets, 8, async (tool) => {
    const official = await replaceWithOfficialIcon(tool);
    if (official.ok) return { type: "downloaded", tool, official };
    const next = path.join(iconDir, `${tool.id}.svg`);
    fs.writeFileSync(next, fallbackSvg(tool), "utf8");
    tool.icon = `assets/icons/tools/${tool.id}.svg`;
    return { type: "generated", tool, official };
});
for (const result of results) {
  if (result.type === "downloaded") {
    downloaded++;
    continue;
  }
  generated++;
  failed.push({ name: result.tool.name, id: result.tool.id, errors: result.official.errors.slice(0, 3) });
}

saveToolData(data);
console.log(JSON.stringify({ downloaded, generated, failed, total: data.tools.length }, null, 2));
