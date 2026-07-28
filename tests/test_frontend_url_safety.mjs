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
    "/StarChart-AI/learn-node.html?slug=rag#overview",
  );
  assert.equal(
    safeInternalHref("/tools.html?q=RAG#directory"),
    "/StarChart-AI/tools.html?q=RAG#directory",
  );
  assert.equal(
    safeInternalHref("/StarChart-AI/assistant.html"),
    "/StarChart-AI/assistant.html",
  );
  assert.equal(safeInternalHref("https://example.com/path"), "#");
  assert.equal(safeInternalHref("javascript:alert(1)"), "#");
});

test("external content links only allow HTTP protocols", () => {
  assert.equal(safeHttpHref("https://example.com/resource"), "https://example.com/resource");
  assert.equal(safeHttpHref("/assets/icon.svg"), "http://localhost/assets/icon.svg");
  assert.equal(safeHttpHref("data:text/html,unsafe"), "#");
  assert.equal(safeHttpHref("javascript:alert(1)"), "#");
});
