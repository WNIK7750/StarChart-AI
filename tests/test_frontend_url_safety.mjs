import assert from "node:assert/strict";
import test from "node:test";

globalThis.window = { location: { origin: "http://localhost" } };

const { safeHttpHref, safeInternalHref } = await import(`../frontend/assets/js/url-safety.js?test=${Date.now()}`);

test("internal links stay on the current origin", () => {
  assert.equal(safeInternalHref("learn-node.html?slug=rag#overview"), "/learn-node.html?slug=rag#overview");
  assert.equal(safeInternalHref("https://example.com/path"), "#");
  assert.equal(safeInternalHref("javascript:alert(1)"), "#");
});

test("external content links only allow HTTP protocols", () => {
  assert.equal(safeHttpHref("https://example.com/resource"), "https://example.com/resource");
  assert.equal(safeHttpHref("/assets/icon.svg"), "http://localhost/assets/icon.svg");
  assert.equal(safeHttpHref("data:text/html,unsafe"), "#");
  assert.equal(safeHttpHref("javascript:alert(1)"), "#");
});
