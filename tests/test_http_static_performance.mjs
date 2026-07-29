import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import test from "node:test";

const fingerprint = "62793ed5";
const assetPath = `frontend/assets/img/brand-mark.${fingerprint}.svg`;

test("brand mark filename matches its content hash and stays compact", () => {
  const asset = fs.readFileSync(assetPath);
  const digest = crypto.createHash("sha256").update(asset).digest("hex");
  assert.equal(digest.slice(0, 8), fingerprint);
  assert.ok(asset.byteLength < 4096, `brand mark is ${asset.byteLength} bytes`);
});

test("HTTP overlay compresses text and only makes the fingerprinted asset immutable", () => {
  const nginx = fs.readFileSync("deploy/http-test/nginx/ai-nav.conf", "utf8");
  assert.match(nginx, /gzip on;/);
  assert.match(nginx, /gzip_vary on;/);
  assert.match(nginx, /gzip_types text\/css application\/javascript application\/json image\/svg\+xml;/);
  assert.match(
    nginx,
    new RegExp(`location = /StarChart-AI/assets/img/brand-mark\\.${fingerprint}\\.svg \\{[\\s\\S]*max-age=31536000, immutable`),
  );
  const fingerprinted = nginx.match(
    new RegExp(`location = /StarChart-AI/assets/img/brand-mark\\.${fingerprint}\\.svg \\{([\\s\\S]*?)\\n    \\}`),
  )?.[1] || "";
  assert.match(fingerprinted, /proxy_hide_header Cache-Control;/);
  const generic = nginx.match(/location \/StarChart-AI\/ \{([\s\S]*?)\n    \}/)?.[1] || "";
  assert.match(generic, /Cache-Control "no-cache"/);
  assert.doesNotMatch(generic, /immutable/);
});

test("HTTP evidence marks a worktree dirty when release-bearing files are untracked", () => {
  const gate = fs.readFileSync("scripts/verify-http-test-deployment.ps1", "utf8");
  assert.match(gate, /git status --porcelain/);
  assert.doesNotMatch(gate, /--untracked-files=no/);
});
