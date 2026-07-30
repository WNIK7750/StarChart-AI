# Assistant Empty State and Startup Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every empty assistant conversation shows the “今天想学什么？” welcome prompts and make root `start.ps1` recover a broken local virtual environment without silently exiting.

**Architecture:** Keep the existing single welcome template and route every empty conversation through `resetConversation()`. Replace the six-line startup script with a staged PowerShell launcher that validates real executability, rebuilds only the exact project `.venv` when necessary, installs dependencies through `python -m pip`, recognizes an already healthy AI Nav instance on port 8088, and preserves actionable errors.

**Tech Stack:** Native ES modules, HTML, Node test runner, PowerShell 7/Windows PowerShell-compatible syntax, Python 3.13 virtual environments, FastAPI/Uvicorn.

## Global Constraints

- Do not read or print real `.env`, Token, Cookie, database content, Provider request, or Provider response.
- Do not enable or call a live Provider.
- Only remove the exact `D:\Web期末作业\ai-nav2\ai-nav-fullstack\.venv` after a failed executable health probe; never remove another directory.
- Keep runtime databases, uploads, logs, screenshots, and temporary probes outside Git.
- Do not stage parent directories, sibling projects, `.venv`, `.env`, release ZIP files, or unrelated files.
- Do not merge the pull request until the user explicitly authorizes merging.
- Local startup success is not HTTP test deployment or production approval.

---

### Task 1: Restore the welcome prompts for every empty conversation

**Files:**
- Modify: `tests/test_agent_frontend.mjs`
- Modify: `frontend/assets/js/assistant-page.js:285-302`

**Interfaces:**
- Consumes: `resetConversation(): void`, the existing `#welcome` template, and `conversation.messages: Array<{role, content}>`.
- Produces: `renderGuestConversation(conversationId)` renders the welcome template when the selected guest conversation has zero messages and renders only messages when it is non-empty.

- [ ] **Step 1: Write the failing frontend contract**

Add this assertion after the existing guest-memory assertions in
`tests/test_agent_frontend.mjs`:

```js
assert.match(
  script,
  /if \(conversation\.messages\.length === 0\) \{\s*resetConversation\(\);\s*\} else \{\s*messages\.replaceChildren\(\);[\s\S]*conversation\.messages\.forEach/,
  "空游客会话必须恢复“今天想学什么？”欢迎区",
);
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
node --test tests/test_agent_frontend.mjs
```

Expected: failure at “空游客会话必须恢复‘今天想学什么？’欢迎区” because the current implementation always clears `#messages` for an existing empty guest conversation.

- [ ] **Step 3: Implement the smallest render correction**

Replace the unconditional clear/loop in `renderGuestConversation()` with:

```js
  if (conversation.messages.length === 0) {
    resetConversation();
  } else {
    messages.replaceChildren();
    conversation.messages.forEach((message) => addMessage(message.role, message.content));
  }
```

Keep `setCurrentSession(conversation.id)` and the existing status text after this branch.

- [ ] **Step 4: Run focused and nearby frontend tests**

Run:

```powershell
node --test tests/test_agent_frontend.mjs tests/test_guest_agent_memory.mjs tests/test_auth_ui.mjs
```

Expected: all tests pass with zero failures.

- [ ] **Step 5: Commit the frontend behavior**

Review and stage only:

```powershell
git diff --check
git add -- frontend/assets/js/assistant-page.js tests/test_agent_frontend.mjs
git diff --cached --name-status
git diff --cached --check
git commit -m "fix: restore assistant empty conversation prompts"
```

Expected staged files: exactly the two files above.

---

### Task 2: Make `start.ps1` self-healing and non-silent

**Files:**
- Create: `tests/test_start_script.mjs`
- Modify: `start.ps1`

**Interfaces:**
- Consumes: optional `-NoPause`, optional `AI_NAV_PYTHON`, `.venv/pyvenv.cfg`, `backend/requirements.txt`, `backend/run.py`, and local endpoints `/api/v1/health` plus `/api/v1/runtime/public`.
- Produces:
  - `Test-PythonCommand([string]$FilePath, [string[]]$PrefixArguments): bool`
  - `Resolve-BasePython(): PSCustomObject` with `FilePath` and `PrefixArguments`
  - `Invoke-CheckedProcess([string]$Stage, [string]$FilePath, [string[]]$Arguments): void`
  - `Test-ExistingAiNav(): bool`
  - process exit code `0` for an already healthy instance and non-zero for setup/start failure.

- [ ] **Step 1: Write the failing startup contract**

Create `tests/test_start_script.mjs`:

```js
import assert from "node:assert/strict";
import fs from "node:fs";

const script = fs.readFileSync("start.ps1", "utf8");

assert.match(script, /param\(\s*\[switch\]\$NoPause\s*\)/);
assert.match(script, /\$ErrorActionPreference\s*=\s*"Stop"/);
assert.match(script, /function Test-PythonCommand/);
assert.match(script, /function Resolve-BasePython/);
assert.match(script, /AI_NAV_PYTHON/);
assert.match(script, /pyvenv\.cfg/);
assert.match(script, /-c",\s*"import sys"/);
assert.match(script, /function Invoke-CheckedProcess/);
assert.match(script, /Remove-Item\s+-LiteralPath\s+\$venvRoot\s+-Recurse\s+-Force/);
assert.match(script, /"\\.venv"/);
assert.match(script, /"-m",\s*"venv"/);
assert.match(script, /"-m",\s*"pip",\s*"install",\s*"-r"/);
assert.match(script, /function Test-ExistingAiNav/);
assert.match(script, /127\.0\.0\.1:8088\/api\/v1\/health/);
assert.match(script, /127\.0\.0\.1:8088\/api\/v1\/runtime\/public/);
assert.match(script, /Read-Host "按 Enter 关闭窗口"/);
assert.match(script, /if \(-not \$NoPause\)/);
assert.doesNotMatch(script, /Get-Content\s+.*\.env|AI_NAV_AGENT_PROVIDER_LIVE_ENABLED\s*=\s*["']1/);

console.log("start script contract tests passed");
```

- [ ] **Step 2: Run the startup contract and confirm RED**

Run:

```powershell
node --test tests/test_start_script.mjs
```

Expected: failure because the current `start.ps1` has no `-NoPause`, runtime health probe, virtual-environment executable probe, checked process wrapper, or failure preservation.

- [ ] **Step 3: Replace the launcher with staged functions**

Implement `start.ps1` with this control flow:

```powershell
param(
  [switch]$NoPause
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$venvRoot = Join-Path $root ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$stage = "初始化"
```

`Test-PythonCommand` must invoke each candidate with its prefix arguments plus
`-c "import sys"` and return `false` on exceptions or non-zero exit:

```powershell
function Test-PythonCommand {
  param([string]$FilePath, [string[]]$PrefixArguments = @())
  if (-not $FilePath -or -not (Test-Path -LiteralPath $FilePath)) { return $false }
  try {
    & $FilePath @PrefixArguments "-c" "import sys" *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}
```

`Resolve-BasePython` must build candidates in this order:

1. `AI_NAV_PYTHON`;
2. the `executable = ...` value from `.venv/pyvenv.cfg`;
3. `Get-Command python -CommandType Application`;
4. `Get-Command py -CommandType Application` with prefix argument `-3`.

Return the first candidate that passes `Test-PythonCommand`; otherwise throw:

```text
未找到可用的 Python。请安装 Python 3.11+，或设置 AI_NAV_PYTHON。
```

`Invoke-CheckedProcess` must run the exact executable and argument array, then
throw `"$Stage 失败，退出码：$LASTEXITCODE"` whenever the exit code is non-zero.

Before removing an unhealthy virtual environment, verify:

```powershell
$resolvedVenv = [IO.Path]::GetFullPath($venvRoot)
if (
  [IO.Path]::GetDirectoryName($resolvedVenv) -ne $root -or
  [IO.Path]::GetFileName($resolvedVenv) -ne ".venv"
) {
  throw "拒绝处理非项目虚拟环境路径。"
}
```

Then use only:

```powershell
Remove-Item -LiteralPath $venvRoot -Recurse -Force
```

Recreate with the resolved base candidate and verify the new
`.venv/Scripts/python.exe` using `Test-PythonCommand`.

Install dependencies with:

```powershell
Invoke-CheckedProcess "依赖安装" $venvPython @(
  "-m", "pip", "install", "-r", (Join-Path $root "backend\requirements.txt")
)
```

`Test-ExistingAiNav` must request both endpoints with a three-second timeout and
return true only when health JSON has `status == "ok"` and runtime JSON has a
non-empty `deploymentProfile`. A failed health probe must not print response
content.

If `Test-ExistingAiNav` is true, print the canonical URL and, unless
`-NoPause`, run:

```powershell
Read-Host "按 Enter 关闭窗口"
```

Otherwise check whether TCP port 8088 is occupied. If occupied, throw a clear
error without stopping that process. If free, start:

```powershell
Invoke-CheckedProcess "应用启动" $venvPython @("backend\run.py")
```

Wrap the complete staged flow in `try/catch`; print the current stage and
`$_.Exception.Message`, pause unless `-NoPause`, and `exit 1`.

- [ ] **Step 4: Run startup contract and PowerShell syntax checks**

Run:

```powershell
node --test tests/test_start_script.mjs
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
  (Resolve-Path "start.ps1"),
  [ref]$tokens,
  [ref]$errors
) | Out-Null
if (@($errors).Count -ne 0) { throw ($errors | Out-String) }
```

Expected: Node test passes and PowerShell parser reports zero errors.

- [ ] **Step 5: Exercise the real self-recovery path**

Keep the currently healthy 8088 process running. Execute:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 -NoPause
```

Expected:

- the existing broken `.venv` fails its executable probe;
- only the exact project `.venv` is rebuilt;
- dependency installation succeeds;
- both 8088 probes identify the existing AI Nav instance;
- the script exits `0` without starting a second listener;
- `netstat -ano` shows exactly one listener on 8088.

Do not inspect or print `.env`. If dependency download is required and sandbox
network blocks it, rerun only this command with the required network approval.

- [ ] **Step 6: Commit the startup repair**

Review and stage only:

```powershell
git status --short
git diff --check
git add -- start.ps1 tests/test_start_script.mjs
git diff --cached --name-status
git diff --cached --check
git commit -m "fix: recover local one-click startup"
```

Expected staged files: exactly `start.ps1` and `tests/test_start_script.mjs`.

---

### Task 3: Run regression gates and rendered acceptance

**Files:**
- Modify only if measured evidence must be corrected:
  `docs/superpowers/specs/2026-07-30-assistant-empty-state-and-startup-recovery-design.md`
- No committed screenshots, databases, logs, or browser scripts.

**Interfaces:**
- Consumes: the fixed guest render branch and the self-healing `start.ps1`.
- Produces: fresh automated, startup, desktop, mobile, and Git-scope evidence for handoff.

- [ ] **Step 1: Run focused and full frontend gates**

Run:

```powershell
node --test tests/test_agent_frontend.mjs tests/test_guest_agent_memory.mjs tests/test_start_script.mjs
node --test tests/*.mjs
.\scripts\verify-frontend.ps1
git diff --check
```

Expected: every command exits `0` with zero failed tests.

- [ ] **Step 2: Verify local routes and capabilities**

Probe:

```text
/
/assistant
/learn
/learn/rag
/tools
/settings
/api/v1/health
/api/v1/runtime/public
/api/v1/agent/capabilities
```

Expected: all return `200`; Agent capabilities retain `sessions=true` for the
existing local acceptance instance.

- [ ] **Step 3: Run desktop and mobile Playwright acceptance**

Browser plugin is not available in this session, so use existing Playwright
through the Node REPL without installing dependencies. Test:

```text
/assistant
→ clear guest history
→ verify “今天想学什么？”
→ click “新建对话” twice
→ after each click verify the heading and all four suggestions
→ send “RAG 怎么学？”
→ verify the welcome area disappears
→ reopen an empty conversation
→ verify the welcome area returns
```

Use viewports `1440x900` and `390x844`. Record page URL/title, meaningful DOM,
framework-overlay absence, relevant console errors, horizontal overflow, and
interaction state. Save screenshots under
`C:\Users\LEGION\AppData\Local\Temp\ai-nav-clean-route-qa\`, outside the repo.

- [ ] **Step 4: Audit Git scope**

Run:

```powershell
git status --short
git diff --stat HEAD~3..HEAD
git diff --check HEAD~3..HEAD
git log -3 --oneline
```

Expected: only the approved design, plan, assistant frontend/test, and startup
script/test files are present in this task’s commits. No parent, sibling,
runtime, secret, database, upload, log, screenshot, or archive path appears.

- [ ] **Step 5: Update task evidence only when facts changed**

If the design status line still says “待实现” after every gate passes, change it
to “本地实现与验收通过；HTTP 测试服务器未部署”, run the secret scanner and
`git diff --check`, then commit only that document:

```powershell
git add -- docs/superpowers/specs/2026-07-30-assistant-empty-state-and-startup-recovery-design.md
git diff --cached --name-status
git diff --cached --check
git commit -m "docs: record startup recovery acceptance"
```

Do not push or merge unless separately authorized.

---

### Follow-up: Make every fixed guest prompt testable locally

**Files:**
- Modify: local guest capability, Agent routing/service/guard, assistant frontend,
  root launcher, and their corresponding tests.

- [x] Reproduce the local guest `404` and confirm `guestChat=false`.
- [x] Add failing tests for the effective guest capability and all four prompts.
- [x] Enable deterministic guest chat only through an explicit local/test switch.
- [x] Gate guest sends against `/runtime/public`.
- [x] Normalize “带我去学习 Transformer” to a learning-plan query.
- [x] Use one fixed answer whenever final grounded evidence is empty.
- [x] Verify all four prompts over HTTP and desktop Playwright.
- [x] Verify the welcome state and RAG response at `390x844`.
- [x] Run Node, frontend, Agent, Foundation, Ruff, route, and Git-scope gates.

The local 8088 acceptance instance is deterministic, has `guestChat=true`, and
retains clean `/assistant` routing. HTTP test server deployment and PR merge
remain separate, explicitly uncompleted tasks.
