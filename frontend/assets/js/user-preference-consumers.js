import { getAccessToken } from "./api.js";
import { getUserPreferenceContext } from "./users-api.js";

const contextCache = new Map();

export async function getConsumerPreferences(consumer) {
  if (!getAccessToken()) return {};
  if (!contextCache.has(consumer)) {
    contextCache.set(
      consumer,
      getUserPreferenceContext(consumer)
        .then((data) => data.preferences || {})
        .catch(() => ({})),
    );
  }
  return contextCache.get(consumer);
}

export function applyLearningResourcePreferences(items, preferences = {}) {
  let result = [...items];
  if (preferences.showExternalResources === false) {
    result = result.filter((item) => item.accessType !== "external");
  }
  if (preferences.cnFirst) {
    result.sort((left, right) => Number(right.accessType === "cn") - Number(left.accessType === "cn"));
  }
  return result;
}

export function applyToolPreferences(items, preferences = {}) {
  const result = [...items];
  if (preferences.freeFirst || preferences.cnFirst) {
    const domesticTags = new Set(["国产", "国内", "中文"]);
    const score = (item) => [
      Number(Boolean(preferences.freeFirst && item.tags?.includes("免费"))),
      Number(Boolean(preferences.cnFirst && item.tags?.some((tag) => domesticTags.has(tag)))),
    ];
    result.sort((left, right) => {
      const leftScore = score(left);
      const rightScore = score(right);
      return rightScore[0] - leftScore[0] || rightScore[1] - leftScore[1];
    });
  }
  return result;
}
