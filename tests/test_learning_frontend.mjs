import test from "node:test";
import assert from "node:assert/strict";

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
