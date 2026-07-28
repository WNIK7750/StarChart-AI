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

test("each non-Agent page has one explicit runtime entry", () => {
  for (const [page, expectedEntry] of Object.entries(pageEntries)) {
    const html = read(page);
    const externalScripts = [...html.matchAll(/<script[^>]+src=["']([^"']+)["'][^>]*>/g)].map((match) => match[1]);
    assert.deepEqual(externalScripts, [expectedEntry], page);
    assert.doesNotMatch(html, /<script(?:\s[^>]*)?>\s*(?!<\/script>)[\s\S]*?<\/script>/i, `${page} contains inline runtime code`);
  }
});

test("each non-Agent page loads the shared accessibility baseline", () => {
  for (const page of Object.keys(pageEntries)) {
    assert.match(
      read(page),
      /<link[^>]+href=["']assets\/css\/accessibility\.css["'][^>]*>/,
      `${page} does not load the shared accessibility baseline`,
    );
  }
});

test("page entries compose shared shell and owned domain runtime", () => {
  assert.match(read("assets/js/home-page.js"), /initPageShell\("home"\)/);
  assert.match(read("assets/js/home-page.js"), /initHomePage\(\)/);
  assert.match(read("assets/js/learn-page.js"), /initLearnPage\(\)/);
  assert.match(read("assets/js/learn-node-page.js"), /initNodePage\(\)/);
  assert.match(read("assets/js/tools-entry.js"), /initToolsPage\(\)/);
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

test("static page links do not point to missing HTML files", () => {
  for (const page of Object.keys(pageEntries).concat("assistant.html")) {
    const html = read(page);
    for (const match of html.matchAll(/href=["']([^"']+\.html)(?:[?#][^"']*)?["']/g)) {
      assert.equal(fs.existsSync(path.join(frontend, match[1])), true, `${page} -> ${match[1]}`);
    }
  }
});

test("home tool fallbacks lead to the tool directory", () => {
  const html = read("index.html");
  const marquee = html.match(/<div class="tools-marquee-track">([\s\S]*?)<\/div>\s*<\/div>\s*<\/section>/)?.[1] || "";
  assert.ok(marquee, "home tool marquee is missing");
  assert.doesNotMatch(marquee, /<a href="#" class="marquee-card">/);
  assert.match(marquee, /<a href="tools\.html\?q=/);
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
  assert.match(home, /hydrateRoadmap\(\{ includeUserState = false \} = \{\}\)/);
  assert.match(home, /if \(includeUserState\) await decorateRoadmapProgress\(canvas\)/);
  assert.doesNotMatch(state, /home-learning-band/);
});

test("settings primary navigation follows the public page order", () => {
  const html = read("settings.html");
  const links = html.match(/<nav class="top-links"[\s\S]*?<\/nav>/)?.[0] || "";
  assert.match(links, /index\.html[\s\S]*learn\.html[\s\S]*tools\.html[\s\S]*assistant\.html[\s\S]*data-auth-root/);
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

test("page shell starts independent navigation and authentication work together", () => {
  const shell = read("assets/js/page-shell.js");
  assert.match(shell, /await Promise\.all\(\[\s*hydrateNavigation\(activeCode\),\s*initAuthUI\(\),\s*\]\)/);
});

test("paged tool sections keep a stable desktop grid footprint", () => {
  const runtime = read("assets/js/tools-page.js");
  const page = read("tools.html");
  assert.match(runtime, /classList\.toggle\('is-paged', totalPages > 1\)/);
  assert.match(runtime, /totalPages > 1 \? ' is-paged' : ''/);
  assert.match(page, /\.category-tools\.is-paged \{ min-height: 490px; grid-auto-rows: 112px; align-content: start; \}/);
  assert.match(page, /@media \(max-width: 760px\)[\s\S]*\.category-tools\.is-paged \{ min-height: 0; \}/);
});
