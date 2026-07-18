import { getAccessToken } from "./api.js";
import { importAnonymousLearning } from "./learning-api.js";

const STORAGE_KEY = "ai_nav_anonymous_learning_v1";
const MAX_NODE_VIEWS = 30;

function createSnapshotId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `anon_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`;
}

function emptyState() {
  return { snapshotId: createSnapshotId(), nodeViews: [] };
}

function readState() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!value?.snapshotId || !Array.isArray(value.nodeViews)) return emptyState();
    return value;
  } catch {
    return emptyState();
  }
}

function writeState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function recordAnonymousNodeView(nodeSlug) {
  if (getAccessToken()) return;
  const state = readState();
  state.nodeViews = state.nodeViews.filter((item) => item.nodeSlug !== nodeSlug);
  state.nodeViews.push({ nodeSlug, viewedAt: new Date().toISOString() });
  state.nodeViews = state.nodeViews.slice(-MAX_NODE_VIEWS);
  writeState(state);
}

export async function mergeAnonymousLearningState() {
  if (!getAccessToken()) return null;
  const state = readState();
  if (!state.nodeViews.length) return null;
  const result = await importAnonymousLearning(state);
  localStorage.removeItem(STORAGE_KEY);
  return result;
}
