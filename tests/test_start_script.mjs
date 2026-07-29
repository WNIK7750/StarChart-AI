import assert from "node:assert/strict";
import fs from "node:fs";

const script = fs.readFileSync("start.ps1", "utf8");

assert.match(script, /param\(\s*\[switch\]\$NoPause\s*\)/);
assert.match(script, /\$ErrorActionPreference\s*=\s*"Stop"/);
assert.match(script, /function Test-PythonCommand/);
assert.match(script, /function Resolve-BasePython/);
assert.match(script, /AI_NAV_PYTHON/);
assert.match(script, /pyvenv\.cfg/);
assert.match(script, /"-c"\s*,\s*"import sys/);
assert.match(script, /function Invoke-CheckedProcess/);
assert.match(script, /Remove-Item\s+-LiteralPath\s+\$venvRoot\s+-Recurse\s+-Force/);
assert.match(script, /"\.venv"/);
assert.match(script, /"-m"\s*,\s*"venv"/);
assert.match(script, /"-m"\s*,\s*"pip"\s*,\s*"install"\s*,\s*"-r"/);
assert.match(script, /function Test-ExistingAiNav/);
assert.match(script, /127\.0\.0\.1:8088\/api\/v1\/health/);
assert.match(script, /127\.0\.0\.1:8088\/api\/v1\/runtime\/public/);
assert.match(script, /AI_NAV_AGENT_GUEST_CHAT_ENABLED/);
assert.match(script, /Read-Host "按 Enter 关闭窗口"/);
assert.match(script, /if \(-not \$NoPause\)/);
assert.doesNotMatch(
  script,
  /Get-Content\s+.*\.env|AI_NAV_AGENT_PROVIDER_LIVE_ENABLED\s*=\s*["']1/,
);

console.log("start script contract tests passed");
