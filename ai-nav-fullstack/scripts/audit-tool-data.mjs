import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dataPath = path.join(root, "frontend/assets/js/tool-data.js");
const listPath = path.join(root, "frontend/assets/js/tool-page-lists.js");

function loadWindowScript(file) {
  const sandbox = { window: {} };
  vm.runInNewContext(fs.readFileSync(file, "utf8"), sandbox, { filename: file });
  return sandbox.window;
}

const dataWindow = loadWindowScript(dataPath);
const listWindow = loadWindowScript(listPath);
const data = dataWindow.AINavToolData;
const lists = listWindow.AINavToolPageLists;
const publishedTools = data.tools.filter((tool) => (tool.publicationStatus || "published") === "published");
const publishedToolIds = new Set(publishedTools.map((tool) => tool.id));

const names = new Map();
const ids = new Map();
for (const tool of data.tools) {
  names.set(tool.name, (names.get(tool.name) || 0) + 1);
  ids.set(tool.id, (ids.get(tool.id) || 0) + 1);
}

const missingIcons = data.tools.filter((tool) => !fs.existsSync(path.join(root, "frontend", tool.icon)));
const duplicateNames = [...names.entries()].filter(([, count]) => count > 1).map(([name]) => name);
const duplicateIds = [...ids.entries()].filter(([, count]) => count > 1).map(([id]) => id);
const missingUrls = data.tools.filter((tool) => !String(tool.url || "").startsWith("https://"));
const categoryIds = new Set(data.categories.map((category) => category.id));
const toolIds = new Set(data.tools.map((tool) => tool.id));
const invalidPlacements = data.placements.filter((placement) => !toolIds.has(placement.toolId) || !categoryIds.has(placement.categoryId));
const missingLatest = lists.latestTools.filter((item) => !dataWindow.AINavFindTool(item.toolName));
const orphanIcons = fs.readdirSync(path.join(root, "frontend/assets/icons/tools"))
  .filter((file) => !data.tools.some((tool) => path.posix.basename(tool.icon) === file));
const placeholderIcons = data.tools.filter((tool) => {
  const iconPath = path.join(root, "frontend", tool.icon || "");
  if (!fs.existsSync(iconPath) || !iconPath.endsWith(".svg")) return false;
  const content = fs.readFileSync(iconPath, "utf8");
  return /<svg\b/i.test(content) && /<linearGradient\b/i.test(content) && /<text\b/i.test(content);
});

const iconBytes = fs.readdirSync(path.join(root, "frontend/assets/icons/tools"))
  .reduce((sum, file) => sum + fs.statSync(path.join(root, "frontend/assets/icons/tools", file)).size, 0);

const report = {
  version: data.version,
  categories: data.categories.length,
  catalogTools: data.tools.length,
  uniqueTools: publishedTools.length,
  archivedTools: data.tools.filter((tool) => tool.publicationStatus === "archived").map((tool) => tool.id),
  placements: data.placements.filter((placement) => publishedToolIds.has(placement.toolId)).length,
  latestSlots: lists.latestTools.length,
  missingIcons: missingIcons.map((tool) => tool.name),
  duplicateNames,
  duplicateIds,
  missingUrls: missingUrls.map((tool) => tool.id),
  invalidPlacements: invalidPlacements.map((placement) => `${placement.toolId}:${placement.categoryId}:${placement.subcategory}`),
  missingLatest: missingLatest.map((item) => item.displayName),
  orphanIcons,
  placeholderIcons: placeholderIcons.map((tool) => tool.name),
  iconBytes,
};

const runtimeBaseUrl = String(process.env.AI_NAV_BASE_URL || "").replace(/\/$/, "");
if (runtimeBaseUrl) {
  const response = await fetch(`${runtimeBaseUrl}/api/v1/tools/catalog`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Runtime tool catalog returned HTTP ${response.status}`);
  const runtime = await response.json();
  const sourceIds = new Set(publishedTools.map((tool) => tool.id));
  const runtimeIds = new Set(runtime.tools.map((tool) => tool.id));
  const isFree = (toolId) => data.placements
    .filter((placement) => placement.toolId === toolId)
    .some((placement) => /免费|开源|\bfree\b|\bopen(?:\s*source)?\b/i.test(String(placement.tag || "")));
  const normalizeCategories = (categories) => categories.map((category) => ({
    id: category.id,
    name: category.name,
    icon: category.icon,
    logoClass: category.logoClass,
    description: category.description,
    subcategories: category.subcategories || ["全部"],
  }));
  const normalizeTools = (tools, source = false) => tools.map((tool) => ({
    id: tool.id,
    name: tool.name,
    aliases: tool.aliases || [],
    description: tool.description,
    mark: tool.mark,
    url: tool.url,
    icon: tool.icon,
    iconFallbacks: tool.iconFallbacks || [],
    isFree: source ? isFree(tool.id) : Boolean(tool.isFree),
    publicationStatus: source ? (tool.publicationStatus || "published") : tool.publicationStatus,
  }));
  const normalizePlacements = (placements) => placements.map((placement) => ({
    toolId: placement.toolId,
    categoryId: placement.categoryId,
    subcategory: placement.subcategory,
    heat: Number(placement.heat) || 0,
    tag: placement.tag || "",
  }));
  const normalizeLatest = (items) => items.map((item) => ({
    displayName: item.displayName,
    toolName: item.toolName,
    provider: item.provider || "",
    label: item.label || "",
    mark: item.mark || "AI",
    logoClass: item.logoClass || "logo-chat",
  }));
  const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
  const fieldMismatches = [];
  if (!same(normalizeCategories(data.categories), normalizeCategories(runtime.categories))) fieldMismatches.push("categories");
  if (!same(normalizeTools(publishedTools, true), normalizeTools(runtime.tools))) fieldMismatches.push("tools");
  if (!same(normalizePlacements(data.placements.filter((placement) => publishedToolIds.has(placement.toolId))), normalizePlacements(runtime.placements))) fieldMismatches.push("placements");
  if (!same(normalizeLatest(lists.latestTools), normalizeLatest(runtime.latestTools))) fieldMismatches.push("latestTools");
  report.runtime = {
    source: runtime.meta?.source,
    categories: runtime.categories.length,
    uniqueTools: runtime.tools.length,
    placements: runtime.placements.length,
    latestSlots: runtime.latestTools.length,
    missingToolIds: [...sourceIds].filter((id) => !runtimeIds.has(id)),
    extraToolIds: [...runtimeIds].filter((id) => !sourceIds.has(id)),
    fieldMismatches,
  };
  report.runtime.passed = report.runtime.source === "tools.database"
    && report.runtime.categories === report.categories
    && report.runtime.uniqueTools === report.uniqueTools
    && report.runtime.placements === report.placements
    && report.runtime.latestSlots === report.latestSlots
    && report.runtime.missingToolIds.length === 0
    && report.runtime.extraToolIds.length === 0
    && report.runtime.fieldMismatches.length === 0;
}

console.log(JSON.stringify(report, null, 2));

if (
  report.missingIcons.length
  || report.duplicateNames.length
  || report.duplicateIds.length
  || report.missingUrls.length
  || report.invalidPlacements.length
  || report.missingLatest.length
  || report.orphanIcons.length
  || report.placeholderIcons.length
  || (report.runtime && !report.runtime.passed)
) {
  process.exitCode = 1;
}
