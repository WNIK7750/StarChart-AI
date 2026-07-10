import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = process.cwd();
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

const names = new Map();
for (const tool of data.tools) {
  names.set(tool.name, (names.get(tool.name) || 0) + 1);
}

const missingIcons = data.tools.filter((tool) => !fs.existsSync(path.join(root, "frontend", tool.icon)));
const duplicateNames = [...names.entries()].filter(([, count]) => count > 1).map(([name]) => name);
const missingLatest = lists.latestTools.filter((item) => !dataWindow.AINavFindTool(item.toolName));
const orphanIcons = fs.readdirSync(path.join(root, "frontend/assets/icons/tools"))
  .filter((file) => !data.tools.some((tool) => path.basename(tool.icon) === file));

const iconBytes = fs.readdirSync(path.join(root, "frontend/assets/icons/tools"))
  .reduce((sum, file) => sum + fs.statSync(path.join(root, "frontend/assets/icons/tools", file)).size, 0);

const report = {
  version: data.version,
  categories: data.categories.length,
  uniqueTools: data.tools.length,
  placements: data.placements.length,
  latestSlots: lists.latestTools.length,
  missingIcons: missingIcons.map((tool) => tool.name),
  duplicateNames,
  missingLatest: missingLatest.map((item) => item.displayName),
  orphanIcons,
  iconBytes,
};

console.log(JSON.stringify(report, null, 2));

if (report.missingIcons.length || report.duplicateNames.length || report.missingLatest.length) {
  process.exitCode = 1;
}
