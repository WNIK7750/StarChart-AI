import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const root = process.cwd();

async function importPageShell() {
  const localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  };
  globalThis.localStorage = localStorage;
  globalThis.window = {
    AI_NAV_PUBLIC_BASE_PATH: "/StarChart-AI",
    location: { origin: "http://localhost" },
    localStorage,
  };
  const moduleUrl = pathToFileURL(path.join(root, "frontend/assets/js/page-shell.js"));
  return import(`${moduleUrl.href}?interaction=${Date.now()}`);
}

test("frame throttling renders the latest pointer coordinates", async () => {
  const { frameThrottle } = await importPageShell();
  const frames = [];
  const rendered = [];
  const throttled = frameThrottle(
    (value) => rendered.push(value),
    (callback) => {
      frames.push(callback);
      return frames.length;
    },
  );

  throttled("first");
  throttled("latest");
  assert.equal(frames.length, 1);
  frames.shift()();
  assert.deepEqual(rendered, ["latest"]);
});

test("shared spotlight and tools interactions avoid per-event layout work", () => {
  const shell = fs.readFileSync("frontend/assets/js/page-shell.js", "utf8");
  const tools = fs.readFileSync("frontend/assets/js/tools-page.js", "utf8");

  const spotlight = shell.match(/export function bindSpotlight[\s\S]*?\n\}/)?.[0] || "";
  assert.match(spotlight, /frameThrottle/);
  assert.match(tools, /function scheduleCardPointerFrame/);
  assert.match(tools, /requestAnimationFrame/);
  assert.match(tools, /function scheduleToolsScrollFrame/);
});
