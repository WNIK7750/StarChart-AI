import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const root = process.cwd();
const frontend = path.join(root, "frontend");
const read = (file) => fs.readFileSync(path.join(frontend, file), "utf8");

const pageEntries = {
  "index.html": "assets/js/home-page.js",
  "learn.html": "assets/js/learn-page.js",
  "learn-node.html": "assets/js/learn-node-page.js",
  "tools.html": "assets/js/tools-entry.js",
  "settings.html": "assets/js/settings.js",
};
const assetHref = (page, asset) => page === "learn-node.html" ? `../${asset}` : asset;

test("each non-Agent page has one explicit runtime entry", () => {
  for (const [page, expectedEntry] of Object.entries(pageEntries)) {
    const html = read(page);
    const externalScripts = [...html.matchAll(/<script[^>]+src=["']([^"']+)["'][^>]*>/g)].map((match) => match[1]);
    assert.deepEqual(externalScripts, [assetHref(page, expectedEntry)], page);
    assert.doesNotMatch(html, /<script(?:\s[^>]*)?>\s*(?!<\/script>)[\s\S]*?<\/script>/i, `${page} contains inline runtime code`);
  }
});

test("each non-Agent page loads the shared accessibility baseline", () => {
  for (const page of Object.keys(pageEntries)) {
    const expectedHref = assetHref(page, "assets/css/accessibility.css");
    assert.match(
      read(page),
      new RegExp(`<link[^>]+href=["']${expectedHref.replaceAll(".", "\\.")}["'][^>]*>`),
      `${page} does not load the shared accessibility baseline`,
    );
  }
});

test("each page preloads its critical module entry before body parsing finishes", () => {
  for (const [page, expectedEntry] of Object.entries(pageEntries)) {
    const expectedHref = assetHref(page, expectedEntry);
    assert.match(
      read(page),
      new RegExp(`<link[^>]+rel=["']modulepreload["'][^>]+href=["']${expectedHref.replaceAll(".", "\\.")}["'][^>]*>`),
      `${page} does not preload ${expectedHref}`,
    );
  }
  const assistant = read("assistant.html");
  for (const entry of ["assets/js/v2-api.js", "assets/js/assistant-page.js"]) {
    assert.match(
      assistant,
      new RegExp(`<link[^>]+rel=["']modulepreload["'][^>]+href=["']${entry.replaceAll(".", "\\.")}["'][^>]*>`),
      `assistant.html does not preload ${entry}`,
    );
  }
});

test("page entries compose shared shell and owned domain runtime", () => {
  assert.match(read("assets/js/home-page.js"), /initPageShell\("home"\)/);
  assert.match(read("assets/js/home-page.js"), /initHomePage\(\)/);
  assert.match(read("assets/js/learn-page.js"), /initLearnPage\(\{\s*authReady:/);
  assert.match(read("assets/js/learn-node-page.js"), /initNodePage\(\{\s*authReady:/);
  assert.match(read("assets/js/tools-entry.js"), /initToolsPage\(\)/);
  assert.match(read("assets/js/tools-entry.js"), /if \(!location\.hash\) window\.scrollTo\(0, 0\)/);
  assert.doesNotMatch(read("assets/js/tools-entry.js"), /history\.replaceState/);
  assert.match(read("assets/js/tools-page.js"), /apiGet\('\/tools\/catalog'\)/);
  assert.match(read("assets/js/tools-page.js"), /meta\.linkStatus === 'unavailable'/);
  assert.doesNotMatch(read("assets/js/tools-page.js"), /baidu\.com\/s\?wd=/);
  assert.doesNotMatch(read("assets/js/tools-page.js"), /fetch\(['"]\/api\/v1\/tools\/catalog/);
});

test("legacy dual-track page scripts are absent", () => {
  for (const file of ["home.js", "learn.js", "node.js", "roadmap.js", "tools.js", "layout.js"]) {
    assert.equal(fs.existsSync(path.join(frontend, "assets", "js", file)), false, file);
  }
});

test("new-window links isolate the opener", () => {
  const files = [
    "learn-node.html",
    "assets/js/learning-pages.js",
    "assets/js/tools-page.js",
  ];
  for (const file of files) {
    const source = read(file);
    const links = [...source.matchAll(/<a\s[^>]*target=["']_blank["'][^>]*>/g)].map((match) => match[0]);
    assert.ok(links.length > 0, `${file} has no audited external links`);
    links.forEach((link) => assert.match(link, /rel=["'][^"']*noopener[^"']*noreferrer[^"']*["']/, `${file}: ${link}`));
  }
});

test("static product navigation uses canonical clean routes", () => {
  for (const page of Object.keys(pageEntries).concat("assistant.html")) {
    const html = read(page);
    assert.doesNotMatch(html, /href=["'][^"']*\.html(?:[?#][^"']*)?["']/i, page);
  }
});

test("home tool fallbacks lead to the tool directory", () => {
  const html = read("index.html");
  const marquee = html.match(/<div class="tools-marquee-track">([\s\S]*?)<\/div>\s*<\/div>\s*<\/section>/)?.[1] || "";
  assert.ok(marquee, "home tool marquee is missing");
  assert.doesNotMatch(marquee, /<a href="#" class="marquee-card">/);
  assert.match(marquee, /<a href="tools\?q=/);
});

test("home stats resolve immediately when reduced motion is requested", () => {
  const source = read("assets/js/home-page.js");
  assert.match(source, /prefers-reduced-motion: reduce/);
  assert.match(source, /stats\.forEach\(\(element\) => setValue\(element, element\.dataset\.target\)\)/);
});

test("home latest tools adapt the wrapped Tools API contract", () => {
  const source = read("assets/js/learning-pages.js");
  assert.match(source, /const tool = item\.tool \|\| item/);
  assert.match(source, /officialUrl: tool\.url/);
  assert.match(source, /iconUrl: tool\.icon/);
});

test("home remains a public navigation surface without user learning state", () => {
  const home = read("assets/js/learning-pages.js");
  const state = read("assets/js/learning-state.js");
  assert.doesNotMatch(home, /hydrateLearningDashboard\(["']home["']\)/);
  assert.match(home, /async function hydrateRoadmap\(\)/);
  assert.doesNotMatch(home, /async function hydrateRoadmap\([^)]*includeUserState/);
  assert.doesNotMatch(state, /home-learning-band/);
});

test("settings primary navigation follows the public page order", () => {
  const html = read("settings.html");
  const links = html.match(/<nav class="top-links"[\s\S]*?<\/nav>/)?.[0] || "";
  assert.match(links, /href="\."[\s\S]*href="learn"[\s\S]*href="tools"[\s\S]*href="assistant"[\s\S]*data-auth-root/);
});

test("nested learning pages resolve every owned asset from the site root", () => {
  const html = read("learn-node.html");
  const ownedAssets = [...html.matchAll(/(?:href|src)=["']([^"']*assets\/[^"']+)["']/g)].map((match) => match[1]);
  assert.ok(ownedAssets.length >= 4, "learn-node.html has too few audited owned assets");
  ownedAssets.forEach((asset) => assert.match(asset, /^\.\.\/assets\//, asset));
});

test("settings keeps unauthenticated visitors on an in-page sign-in gate", () => {
  const html = read("settings.html");
  const runtime = read("assets/js/settings.js");
  const guard = runtime.match(/function requireLogin\(user\) \{([\s\S]*?)\n\}/)?.[1] || "";

  assert.match(html, /data-settings-login-required/);
  assert.match(html, /data-settings-content/);
  assert.match(html, /data-auth-trigger="login"/);
  assert.match(runtime, /function renderLoginRequired\(\)/);
  assert.match(runtime, /const user = requireLogin\(await initAuthUI\(\)\)/);
  assert.doesNotMatch(guard, /window\.location/);
});

test("public page entries do not block domain work on navigation or authentication", () => {
  const shell = read("assets/js/page-shell.js");
  assert.match(shell, /return Promise\.all\(\[\s*hydrateNavigation\(activeCode\),\s*initAuthUI\(\),\s*\]\)/);
  for (const entry of Object.values(pageEntries).filter((entry) => !entry.endsWith("settings.js"))) {
    assert.doesNotMatch(read(entry), /await initPageShell\(/, entry);
    assert.match(read(entry), /(?:void initPageShell\(|const shellReady = initPageShell\()/, entry);
  }
});

test("all pages use one small fingerprinted brand asset", () => {
  const pages = [...Object.keys(pageEntries), "assistant.html"];
  const assets = pages.map((page) => {
    const html = read(page);
    assert.doesNotMatch(html, /assets\/img\/logo\.png/, page);
    return html.match(/assets\/img\/(brand-mark\.[a-f0-9]{8}\.svg)/)?.[1] || "";
  });
  assert.ok(assets.every(Boolean), "one or more pages do not reference a fingerprinted brand asset");
  assert.equal(new Set(assets).size, 1, "pages use different brand asset versions");
  const asset = path.join(frontend, "assets", "img", assets[0]);
  assert.equal(fs.existsSync(asset), true, asset);
  assert.ok(fs.statSync(asset).size < 4096, "brand asset must stay below 4 KiB");
  assert.match(read("assets/js/auth-ui.js"), new RegExp(assets[0].replaceAll(".", "\\.")));
  const settingsRuntime = read("assets/js/settings.js");
  assert.match(settingsRuntime, new RegExp(assets[0].replaceAll(".", "\\.")));
  assert.match(
    settingsRuntime,
    /withPublicBasePath\("\/assets\/img\/brand-mark\.[a-f0-9]{8}\.svg"\)/,
  );
  assert.doesNotMatch(settingsRuntime, /assets\/img\/logo\.png/);
});

test("paged tool sections keep a stable desktop grid footprint", () => {
  const runtime = read("assets/js/tools-page.js");
  const page = read("tools.html");
  assert.match(runtime, /classList\.toggle\('is-paged', totalPages > 1\)/);
  assert.match(runtime, /totalPages > 1 \? ' is-paged' : ''/);
  assert.match(page, /\.category-tools\.is-paged \{ min-height: 490px; grid-auto-rows: 112px; align-content: start; \}/);
  assert.match(page, /@media \(max-width: 760px\)[\s\S]*\.category-tools\.is-paged \{ min-height: 0; \}/);
});
