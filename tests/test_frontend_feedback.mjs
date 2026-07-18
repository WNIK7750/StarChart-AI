import assert from "node:assert/strict";
import test from "node:test";

const elements = new Map();
globalThis.document = {
  getElementById: (id) => elements.get(id) || null,
  createElement: () => ({ id: "", textContent: "" }),
  head: { appendChild: (element) => elements.set(element.id, element) },
};

const { feedbackKindForError, feedbackMarkup } = await import(`../frontend/assets/js/ui-feedback.js?test=${Date.now()}`);

test("shared feedback escapes server messages and exposes stable action keys", () => {
  const html = feedbackMarkup({
    kind: "error",
    title: "加载失败",
    message: '<img src=x onerror="alert(1)">',
    actionLabel: "重试",
    actionKey: "retry-content",
  });
  assert.match(html, /role="alert"/);
  assert.match(html, /data-feedback-action="retry-content"/);
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
});

test("offline errors select the offline presentation", () => {
  assert.equal(feedbackKindForError({ code: "API_OFFLINE" }), "offline");
  assert.equal(feedbackKindForError({ code: "API_TIMEOUT" }), "error");
});
