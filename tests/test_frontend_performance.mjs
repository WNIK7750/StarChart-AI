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
  return import(`${moduleUrl.href}?performance=${Date.now()}`);
}

test("frame throttle schedules at most one callback per animation frame", async () => {
  const { frameThrottle } = await importPageShell();
  const frames = [];
  const values = [];
  const throttled = frameThrottle(
    () => values.push("render"),
    (callback) => {
      frames.push(callback);
      return frames.length;
    },
  );

  for (let index = 0; index < 100; index += 1) throttled();
  assert.equal(frames.length, 1);
  assert.deepEqual(values, []);
  frames.shift()();
  assert.deepEqual(values, ["render"]);
  throttled();
  assert.equal(frames.length, 1);
});

test("home scroll progress uses the shared frame throttle", () => {
  const source = fs.readFileSync("frontend/assets/js/home-page.js", "utf8");
  assert.match(source, /frameThrottle/);
  assert.match(source, /window\.addEventListener\("scroll", frameThrottle\(\(\) =>/);
});

test("frame buffer preserves all text and flushes pending work immediately", async () => {
  const { createFrameBuffer } = await importPageShell();
  const frames = new Map();
  const cancelled = [];
  const rendered = [];
  let nextId = 0;
  const buffer = createFrameBuffer(
    (chunk) => rendered.push(chunk),
    {
      schedule: (callback) => {
        nextId += 1;
        frames.set(nextId, callback);
        return nextId;
      },
      cancel: (id) => {
        cancelled.push(id);
        frames.delete(id);
      },
    },
  );

  for (let index = 0; index < 100; index += 1) buffer.push(String(index % 10));
  assert.equal(frames.size, 1);
  buffer.flush();
  assert.deepEqual(cancelled, [1]);
  assert.equal(rendered.join(""), "0123456789".repeat(10));
  assert.equal(frames.size, 0);

  buffer.push("A");
  const callback = frames.get(2);
  callback();
  assert.equal(rendered.join(""), `${"0123456789".repeat(10)}A`);
});

test("search input cancels stale requests and delays burst input", () => {
  const source = fs.readFileSync("frontend/assets/js/site-search.js", "utf8");
  assert.match(source, /const SEARCH_DEBOUNCE_MS = 180/);
  assert.match(source, /form\._searchController\?\.abort\(\)/);
  assert.match(source, /new AbortController\(\)/);
  assert.match(source, /form\._searchSequence/);
  assert.match(source, /\{ retryCount: 0, signal \}/);
  assert.match(source, /window\.setTimeout\([^,]+,\s*SEARCH_DEBOUNCE_MS\)/s);
});

test("long offscreen sections can skip layout and paint without leaving the accessibility tree", () => {
  const css = fs.readFileSync("frontend/assets/css/accessibility.css", "utf8");
  assert.match(css, /@supports \(content-visibility: auto\)/);
  assert.match(css, /content-visibility: auto/);
  assert.match(css, /contain-intrinsic-size: auto/);
  const optimized = css.match(/@supports \(content-visibility: auto\) \{([\s\S]*?)\n\}/)?.[1] || "";
  assert.doesNotMatch(optimized, /(^|\s)\.directory(?:,|\s*\{)/);
});

test("settings binds the page without waiting for every secondary account area", () => {
  const source = fs.readFileSync("frontend/assets/js/settings.js", "utf8");
  const init = source.match(/async function init\(\) \{([\s\S]*?)\n\}/)?.[1] || "";
  assert.doesNotMatch(init, /await loadAtomicAreas\(\)/);
  assert.match(init, /void loadAtomicAreas\(\)\.catch/);
});
