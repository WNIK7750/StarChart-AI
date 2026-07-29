import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const modulePath = path.resolve("frontend/assets/js/roadmap-tabs.js");

test("home and learning pages use the shared roadmap tab component", () => {
  const home = fs.readFileSync("frontend/index.html", "utf8");
  const learn = fs.readFileSync("frontend/learn.html", "utf8");
  const pages = fs.readFileSync("frontend/assets/js/learning-pages.js", "utf8");

  for (const html of [home, learn]) {
    assert.match(html, /assets\/css\/roadmap-tabs\.css/);
    assert.match(html, /class="roadmap-tabs reveal" role="tablist"/);
    assert.equal((html.match(/class="roadmap-tab active"/g) || []).length, 1);
  }
  assert.doesNotMatch(learn, /\bline-tabs?\b/);
  assert.match(pages, /bindRoadmapTabs/);
  assert.match(pages, /const slugs = data\.domainNodes\[domain\] \|\| \[\]/);
  assert.match(pages, /node\.classList\.toggle\("domain-selected", selected\)/);
  assert.doesNotMatch(pages, /\.line-tab/);
  assert.equal(fs.existsSync(modulePath), true, "shared roadmap tab runtime is missing");
});

test("roadmap tabs keep exactly one selected category", async () => {
  assert.equal(fs.existsSync(modulePath), true, "shared roadmap tab runtime is missing");
  const moduleUrl = pathToFileURL(modulePath);
  moduleUrl.searchParams.set("test", Date.now().toString());
  const { bindRoadmapTabs } = await import(moduleUrl.href);

  const makeTab = (domain, active = false) => {
    const classes = new Set(active ? ["roadmap-tab", "active"] : ["roadmap-tab"]);
    const listeners = new Map();
    return {
      dataset: { domain },
      style: {
        getPropertyValue(name) {
          return name === "--domain-color" ? domain : `${domain}-glow`;
        },
      },
      classList: {
        contains(name) { return classes.has(name); },
        toggle(name, enabled) {
          if (enabled) classes.add(name);
          else classes.delete(name);
        },
      },
      attributes: new Map(),
      setAttribute(name, value) { this.attributes.set(name, value); },
      addEventListener(name, listener) { listeners.set(name, listener); },
      click() { listeners.get("click")?.(); },
    };
  };

  const tabs = [
    makeTab("core", true),
    makeTab("ml"),
    makeTab("dl"),
  ];
  const selections = [];
  const scope = { querySelectorAll: () => tabs };

  bindRoadmapTabs(scope, (selection) => selections.push(selection.domain));
  tabs[1].click();
  tabs[2].click();

  assert.deepEqual(selections, ["core", "ml", "dl"]);
  assert.deepEqual(
    tabs.map((tab) => tab.classList.contains("active")),
    [false, false, true],
  );
  assert.deepEqual(
    tabs.map((tab) => tab.attributes.get("aria-selected")),
    ["false", "false", "true"],
  );
});

test("roadmap category highlighting takes precedence over learning progress", () => {
  const learningState = fs.readFileSync("frontend/assets/js/learning-state.js", "utf8");

  assert.match(
    learningState,
    /\.km-canvas:not\(\.has-domain\) \.km-node\.learning-in-progress \.km-node-rect/,
  );
  assert.match(
    learningState,
    /\.km-canvas:not\(\.has-domain\) \.km-node\.learning-completed \.km-node-rect/,
  );
  assert.match(
    learningState,
    /\.km-canvas:not\(\.has-domain\) \.km-node\.learning-completed \.km-node-dot/,
  );
});
