import assert from "node:assert/strict";
import test from "node:test";

globalThis.window = {
  AI_NAV_PUBLIC_BASE_PATH: "/StarChart-AI",
  location: {
    origin: "http://localhost",
    href: "http://localhost/StarChart-AI/index.html",
  },
};

const { safeHttpHref, safeInternalHref } = await import(`../frontend/assets/js/url-safety.js?test=${Date.now()}`);

test("internal links stay inside the current deployment prefix", () => {
  assert.equal(
    safeInternalHref("learn-node.html?slug=rag#overview"),
    "/StarChart-AI/learn/rag#overview",
  );
  assert.equal(
    safeInternalHref("/tools.html?q=RAG#directory"),
    "/StarChart-AI/tools?q=RAG#directory",
  );
  assert.equal(
    safeInternalHref("/StarChart-AI/assistant.html"),
    "/StarChart-AI/assistant",
  );
  assert.equal(safeInternalHref("https://example.com/path"), "#");
  assert.equal(safeInternalHref("javascript:alert(1)"), "#");
});

test("legacy product links project to canonical clean routes", () => {
  assert.equal(safeInternalHref("index.html#about"), "/StarChart-AI/#about");
  assert.equal(safeInternalHref("assistant.html"), "/StarChart-AI/assistant");
  assert.equal(safeInternalHref("learn.html"), "/StarChart-AI/learn");
  assert.equal(
    safeInternalHref("learn-node.html?slug=rag&source=search#overview"),
    "/StarChart-AI/learn/rag?source=search#overview",
  );
  assert.equal(
    safeInternalHref("tools.html?q=RAG#directory"),
    "/StarChart-AI/tools?q=RAG#directory",
  );
  assert.equal(
    safeInternalHref("settings.html?workflow=wf_1#workflows"),
    "/StarChart-AI/settings?workflow=wf_1#workflows",
  );
  assert.equal(
    safeInternalHref("learn-node.html?slug=Bad_Slug#overview"),
    "/StarChart-AI/learn#overview",
  );
});

test("external content links only allow HTTP protocols", () => {
  assert.equal(safeHttpHref("https://example.com/resource"), "https://example.com/resource");
  assert.equal(safeHttpHref("/assets/icon.svg"), "http://localhost/assets/icon.svg");
  assert.equal(safeHttpHref("data:text/html,unsafe"), "#");
  assert.equal(safeHttpHref("javascript:alert(1)"), "#");
});
