# Local Deployment Control Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn root `start.ps1` into a repeatable local deployment controller that keeps its interactive window open and safely restarts or stops only its own service.

**Architecture:** Store launcher state, logs, and dependency fingerprints under a repository-keyed directory in `%LOCALAPPDATA%`. Launch `backend/run.py` as a managed background process, verify PID plus creation time plus command line before process-tree operations, and expose the same primitives through an interactive menu and `-NoPause`/`-Restart`/`-Stop` switches.

**Tech Stack:** PowerShell 5.1-compatible syntax, Python 3.11+, FastAPI/Uvicorn, Node test runner.

## Global Constraints

- Never read or print real `.env`, tokens, cookies, database contents, or Provider traffic.
- Never enable a live Provider.
- Never stop an unverified process or an unknown 8088 listener.
- Write runtime state and logs outside the repository.
- Preserve `-NoPause` for automation and keep the default interactive window open.
- Do not push or merge unless separately authorized.

---

### Task 1: Lock the deployment-controller contract

**Files:**
- Modify: `tests/test_start_script.mjs`

**Interfaces:**
- Consumes: root `start.ps1` as UTF-8 text.
- Produces: assertions for `-Restart`, `-Stop`, state/log paths, requirements fingerprinting, process ownership validation, readiness polling, and the `R/S/Q` menu.

- [ ] **Step 1: Add failing contract assertions**

Assert that the script contains:

```js
assert.match(script, /\[switch\]\$Restart/);
assert.match(script, /\[switch\]\$Stop/);
assert.match(script, /LocalApplicationData/);
assert.match(script, /Get-FileHash/);
assert.match(script, /function Test-ManagedProcess/);
assert.match(script, /function Stop-ManagedService/);
assert.match(script, /function Start-ManagedService/);
assert.match(script, /function Wait-AiNavReady/);
assert.match(script, /Read-Host "\[R\].*\[S\].*\[Q\]/);
```

- [ ] **Step 2: Run the contract and verify RED**

Run:

```powershell
node --test tests/test_start_script.mjs
```

Expected: failure on the first missing switch.

- [ ] **Step 3: Commit the red contract together with the implementation in Task 2**

Do not commit a deliberately failing branch state separately.

---

### Task 2: Implement managed background deployment

**Files:**
- Modify: `start.ps1`
- Test: `tests/test_start_script.mjs`

**Interfaces:**
- Consumes: `backend/requirements.txt`, `.venv`, health and public-runtime endpoints.
- Produces:
  - `Test-ManagedProcess(): bool`
  - `Stop-ManagedService(): void`
  - `Start-ManagedService(): void`
  - `Wait-AiNavReady([int]$TimeoutSeconds): bool`
  - switches `-NoPause`, `-Restart`, `-Stop`

- [ ] **Step 1: Add repository-keyed runtime paths**

Use SHA-256 of the normalized repository root and the first 16 lowercase hex
characters to create:

```text
%LOCALAPPDATA%\AI-Nav\launcher\<key>\state.json
%LOCALAPPDATA%\AI-Nav\launcher\<key>\stdout.log
%LOCALAPPDATA%\AI-Nav\launcher\<key>\stderr.log
%LOCALAPPDATA%\AI-Nav\launcher\<key>\requirements.sha256
```

- [ ] **Step 2: Add strict ownership validation**

Read state JSON, resolve the current `Win32_Process`, and require matching root,
PID, creation time, executable name/path, and `backend\run.py` command line.
Return false and remove only the stale state file on mismatch.

- [ ] **Step 3: Add dependency fingerprinting**

Install dependencies only after virtual-environment creation or when the
requirements hash differs. Write the new hash only after pip exits `0`.

- [ ] **Step 4: Add background start and readiness polling**

Use `Start-Process -PassThru -WindowStyle Hidden`, separate stdout/stderr logs,
and a condition loop against `/api/v1/health` plus `/api/v1/runtime/public`.
On a 30-second timeout, stop only the just-created managed process and fail with
the log paths.

- [ ] **Step 5: Add safe stop and restart**

Resolve descendants from `Win32_Process`, stop descendants deepest-first, then
the recorded parent. Remove only this launcher's state file. Refuse to operate
when ownership validation fails.

- [ ] **Step 6: Add the persistent control menu**

After deployment, default interactive mode loops on:

```text
[R] 重新部署  [S] 关闭服务  [Q] 退出控制窗口  [Enter] 刷新状态
```

`R` executes stop then start; `S` stops but keeps the menu open; `Q` leaves the
managed service untouched. `-NoPause` skips the menu.

- [ ] **Step 7: Run contract tests and verify GREEN**

Run:

```powershell
node --test tests/test_start_script.mjs
```

Expected: pass.

---

### Task 3: Exercise every lifecycle transition

**Files:**
- Modify: `docs/superpowers/specs/2026-07-30-local-deployment-control-window-design.md`

**Interfaces:**
- Consumes: the completed `start.ps1`.
- Produces: fresh acceptance evidence and final design status.

- [ ] **Step 1: Parse PowerShell**

Run `System.Management.Automation.Language.Parser.ParseFile` and require zero
errors.

- [ ] **Step 2: Stop the currently verified project instance**

Use the existing exact PID inspection before stopping the pre-feature local
process. Do not stop any unknown listener.

- [ ] **Step 3: Verify first start and repeat start**

Run `start.ps1 -NoPause` twice. Require exit `0`, one healthy listener, and the
same managed PID on the second run.

- [ ] **Step 4: Verify restart**

Run `start.ps1 -Restart -NoPause`. Require exit `0`, a changed managed PID, and
healthy `/assistant` plus guest runtime capability.

- [ ] **Step 5: Verify stop and start**

Run `start.ps1 -Stop -NoPause`, require no listener, then run
`start.ps1 -NoPause` and require health restored.

- [ ] **Step 6: Run project gates**

Run:

```powershell
node --test tests/*.mjs
.\scripts\verify-frontend.ps1
.\scripts\verify-foundation.ps1
git diff --check
```

Restore only machine evidence files generated by those gates and confirmed clean
before the run.

- [ ] **Step 7: Record acceptance and commit**

Change the design status to “本地实现与验收通过”, scan only modified files for
credentials, stage exact repository paths, audit the cached diff, and commit:

```text
fix: add one-click deployment controls
```

Do not push or merge.

## Execution outcome

All three tasks were executed inline under the user's explicit approval to use
the recommended solution without an additional review pause. The acceptance
evidence is recorded in the paired design document. The final managed service
is running on `127.0.0.1:8088`; remote HTTP deployment and PR merge remain out
of scope.
