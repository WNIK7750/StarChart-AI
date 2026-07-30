import assert from "node:assert/strict";
import fs from "node:fs";

const script = fs.readFileSync("start.ps1", "utf8");

assert.doesNotMatch(script, /[^\x00-\x7F]/);
assert.match(script, /param\([\s\S]*\[switch\]\$NoPause/);
assert.match(script, /\[switch\]\$Restart/);
assert.match(script, /\[switch\]\$Stop/);
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
assert.match(
  script,
  /AI_NAV_AGENT_SESSIONS_ENABLED\)\)\s*\{\s*\$env:AI_NAV_AGENT_SESSIONS_ENABLED = "1"/,
);
assert.match(script, /runtime\.agent\.authenticatedSessions/);
assert.match(script, /LocalApplicationData/);
assert.match(script, /Get-FileHash/);
assert.match(script, /requirements\.sha256/);
assert.match(script, /state\.json/);
assert.match(script, /UTF8Encoding\(\$true\)/);
assert.match(script, /stdout\.log/);
assert.match(script, /stderr\.log/);
assert.match(script, /function Test-ManagedProcess/);
assert.match(script, /CreationDate/);
assert.match(script, /CommandLine/);
assert.match(script, /function Stop-ManagedService/);
assert.match(script, /function Start-ManagedService/);
assert.match(script, /function Wait-AiNavReady/);
assert.match(script, /Start-Process[\s\S]+-PassThru/);
assert.match(script, /Start-Process[\s\S]+-WindowStyle\s+Hidden/);
assert.match(script, /Read-Host "\[R\].*\[S\].*\[Q\]/);
assert.match(script, /Redeploy/);
assert.match(script, /Stop service/);
assert.doesNotMatch(script, /Join-Path\s+\$root\s+["']\.runtime/);
assert.match(script, /Read-Host "Press Enter to close"/);
assert.match(script, /if \(-not \$NoPause\)/);
assert.doesNotMatch(
  script,
  /Get-Content\s+.*\.env|AI_NAV_AGENT_PROVIDER_LIVE_ENABLED\s*=\s*["']1/,
);

console.log("start script contract tests passed");
