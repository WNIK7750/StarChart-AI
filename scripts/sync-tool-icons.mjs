import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = process.cwd();
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

function isBadIcon(file) {
  if (!fs.existsSync(file)) return true;
  const head = fs.readFileSync(file).subarray(0, 160).toString("utf8").trim().toLowerCase();
  return head.startsWith("<!doctype html") || head.startsWith("<html") || head.includes("<html");
}

const data = loadToolData();
fs.mkdirSync(iconDir, { recursive: true });

let generated = 0;
for (const tool of data.tools) {
  const current = path.join(root, "frontend", tool.icon);
  if (!isBadIcon(current)) continue;
  const next = path.join(iconDir, `${tool.id}.svg`);
  fs.writeFileSync(next, fallbackSvg(tool), "utf8");
  tool.icon = `assets/icons/tools/${tool.id}.svg`;
  generated++;
}

saveToolData(data);
console.log(JSON.stringify({ generated, total: data.tools.length }, null, 2));
