import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

import { formatLearningTime, learningTimeTitle } from "../frontend/assets/js/time-format.js";

test("learning timestamps are localized from UTC database values", () => {
  const now = Date.parse("2026-07-12T08:00:00Z");
  assert.equal(formatLearningTime("2026-07-12 07:59:30", now), "刚刚");
  assert.equal(formatLearningTime("2026-07-12 07:45:00", now), "15 分钟前");
  assert.equal(formatLearningTime("2026-07-12 05:00:00", now), "3 小时前");
  assert.equal(formatLearningTime("2026-07-10 08:00:00", now), "2 天前");
  assert.ok(learningTimeTitle("2026-07-12 07:45:00"));
});

test("invalid timestamps fall back without throwing", () => {
  assert.equal(formatLearningTime("not-a-date"), "最近阅读");
  assert.equal(learningTimeTitle(""), "");
});

test("learning page hydrates independent surfaces concurrently", () => {
  const source = fs.readFileSync("frontend/assets/js/learning-pages.js", "utf8");
  const init = source.match(/export async function initLearnPage\([\s\S]*?\) \{([\s\S]*?)\n\}/)?.[1] || "";
  assert.match(
    init,
    /const publicHydration = Promise\.all\(\[\s*hydrateRoadmap\(\),\s*hydrateLearningResources\(""\),?\s*\]\)/,
  );
  assert.match(init, /Promise\.all\(\[\s*decorateRoadmapProgress[\s\S]*hydrateLearningDashboard\(isCurrent\)/);
});

test("learning node renders public content before optional user preferences", () => {
  const source = fs.readFileSync("frontend/assets/js/learning-pages.js", "utf8");
  const init = source.match(/export async function initNodePage\([\s\S]*?\) \{([\s\S]*?)\n\}/)?.[1] || "";
  assert.match(init, /const nodePayload = await getLearningNode\(slug\)/);
  assert.match(init, /renderNodeResourceList\(mainMaterial, resources\)/);
  assert.match(init, /observeAuthenticatedLearning\([\s\S]*getConsumerPreferences\("learning"\)/);
  assert.doesNotMatch(init, /const preferences = await getConsumerPreferences/);
});

test("learning user state waits for restored authentication without blocking public content", () => {
  const source = fs.readFileSync("frontend/assets/js/learning-pages.js", "utf8");
  assert.match(source, /export async function initLearnPage\(\{ authReady/);
  assert.match(source, /export async function initNodePage\(\{ authReady/);
  assert.match(source, /Promise\.resolve\(authReady\)\s*\.then/);
  assert.match(source, /hydrateRoadmap\(\)/);
  assert.doesNotMatch(source, /hydrateRoadmap\(\{ includeUserState: true \}\)/);

  const learnEntry = fs.readFileSync("frontend/assets/js/learn-page.js", "utf8");
  const nodeEntry = fs.readFileSync("frontend/assets/js/learn-node-page.js", "utf8");
  [learnEntry, nodeEntry].forEach((entry) => {
    assert.match(entry, /const shellReady = initPageShell\("learn"\)/);
    assert.match(entry, /authReady: shellReady\.then\(\(\[, user\]\) => user\)/);
    assert.doesNotMatch(entry, /await initPageShell\(/);
  });
});

test("learning pages hydrate user state after an in-page login exactly once", () => {
  const source = fs.readFileSync("frontend/assets/js/learning-pages.js", "utf8");
  assert.match(source, /function observeAuthenticatedLearning\(/);
  assert.match(source, /window\.addEventListener\("ai-nav-auth-changed"/);
  assert.match(source, /event\.detail\?\.authenticated/);
  assert.match(source, /if \(authenticatedHydrated\) return hydrationPromise/);
  assert.match(source, /observeAuthenticatedLearning\(authReady/);
});

test("learning identity changes invalidate stale account hydration before DOM updates", () => {
  const pages = fs.readFileSync("frontend/assets/js/learning-pages.js", "utf8");
  const state = fs.readFileSync("frontend/assets/js/learning-state.js", "utf8");
  const preferences = fs.readFileSync("frontend/assets/js/user-preference-consumers.js", "utf8");
  assert.match(pages, /new AssistantSessionEpoch\(getAccessToken\(\)\)/);
  assert.match(pages, /epoch\.transition\(getAccessToken\(\)\)/);
  assert.match(pages, /hydrate\(operation\.isCurrent\)/);
  assert.match(pages, /reset\?\.\(\)/);
  assert.match(pages, /resetLearningPageUserState/);
  assert.match(pages, /resetNodeLearningState/);
  assert.match(state, /hydrateLearningDashboard\(isCurrent = \(\) => true\)/);
  assert.match(state, /decorateRoadmapProgress\(scope = document, isCurrent = \(\) => true\)/);
  assert.match(state, /hydrateNodeLearningState\(slug, nodeData, isCurrent = \(\) => true\)/);
  assert.match(state, /let dashboardToken = ""/);
  assert.match(state, /dashboardToken !== token/);
  assert.match(preferences, /let contextToken = ""/);
  assert.match(preferences, /contextCache\.clear\(\)/);
});
