import assert from "node:assert/strict";
import test from "node:test";

globalThis.window = {
  AI_NAV_PUBLIC_BASE_PATH: "",
};

const {
  normalizePublicBasePath,
  detectPublicBasePath,
  withPublicBasePath,
} = await import(`../frontend/assets/js/public-path.js?test=${Date.now()}`);

test("public base paths normalize root and one trailing slash", () => {
  assert.equal(normalizePublicBasePath(""), "");
  assert.equal(normalizePublicBasePath("/"), "");
  assert.equal(normalizePublicBasePath("/StarChart-AI/"), "/StarChart-AI");
});

test("module URLs detect root and subpath deployments", () => {
  delete window.AI_NAV_PUBLIC_BASE_PATH;
  try {
    assert.equal(
      detectPublicBasePath("http://example.test/assets/js/public-path.js"),
      "",
    );
    assert.equal(
      detectPublicBasePath("http://example.test/StarChart-AI/assets/js/public-path.js"),
      "/StarChart-AI",
    );
  } finally {
    window.AI_NAV_PUBLIC_BASE_PATH = "";
  }
});

test("browser paths receive one canonical deployment prefix", () => {
  assert.equal(withPublicBasePath("/uploads/avatars/user.webp", ""), "/uploads/avatars/user.webp");
  assert.equal(
    withPublicBasePath("/uploads/avatars/user.webp", "/StarChart-AI/"),
    "/StarChart-AI/uploads/avatars/user.webp",
  );
  assert.equal(
    withPublicBasePath("/StarChart-AI/uploads/avatars/user.webp", "/StarChart-AI"),
    "/StarChart-AI/uploads/avatars/user.webp",
  );
});

test("unsafe and double-prefixed browser paths are rejected", () => {
  assert.throws(
    () => normalizePublicBasePath("/StarChart-AI//"),
    /public path/i,
  );
  for (const value of [
    "https://example.test/uploads/avatar.webp",
    "//example.test/uploads/avatar.webp",
    "/uploads/../admin",
    "/uploads%2Favatars/user.webp",
    "/uploads%5Cavatars/user.webp",
    "/StarChart-AI%2Fuploads/avatars/user.webp",
    "/StarChart-AI/StarChart-AI/uploads/avatar.webp",
  ]) {
    assert.throws(
      () => withPublicBasePath(value, "/StarChart-AI"),
      /public path/i,
      value,
    );
  }
});
