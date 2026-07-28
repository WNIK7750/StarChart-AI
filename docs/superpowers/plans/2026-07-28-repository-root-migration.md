# Repository Root Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `D:\Web期末作业\ai-nav2\ai-nav-fullstack` the only Git repository root and make its project files appear directly at the root of `WNIK7750/StarChart-AI`.

**Architecture:** Build and verify a clean candidate in an isolated temporary clone of the existing parent repository. Preserve the committed history for `ai-nav-fullstack/`, lift that prefix to the new repository root, apply the current workspace changes without reading or copying real environment files, then publish a candidate branch before any default-branch replacement.

**Tech Stack:** Git, GitHub, PowerShell, GitHub Actions, existing project verification scripts.

## Global Constraints

- Never read, print, copy, commit, or modify a real `.env`.
- Preserve all current tracked and untracked workspace changes.
- Do not rewrite or force-push `master` until the candidate branch is independently verified.
- Do not include sibling projects such as `agent/`, `assets/`, `design/`, or legacy root web files.
- Do not include temporary CI output, runtime databases, credentials, cookies, tokens, or generated release evidence.
- Keep the current remote URL `https://github.com/WNIK7750/StarChart-AI.git`.
- The final local Git root must be `D:\Web期末作业\ai-nav2\ai-nav-fullstack`.

---

### Task 1: Capture the source and safety baseline

**Files:**
- Create: local ignored repository backup bundle under `.repo-backups/`
- Inspect: `.gitignore`
- Inspect: repository refs, remotes, tracked paths, and working-tree status

**Interfaces:**
- Consumes: parent Git repository at `D:\Web期末作业\ai-nav2`
- Produces: immutable bundle backup and a recorded source commit ID

- [ ] **Step 1: Confirm repository boundaries and current state**

Run:

```powershell
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short --branch
git remote -v
```

Expected: the old root is `D:\Web期末作业\ai-nav2`, and the current workspace changes remain visible.

- [ ] **Step 2: Confirm backup storage is ignored**

Run:

```powershell
git check-ignore -v ai-nav-fullstack/.repo-backups/probe.bundle
```

Expected: `.repo-backups/` is ignored. If it is not ignored, add only that path to `ai-nav-fullstack/.gitignore`.

- [ ] **Step 3: Create and verify a complete bundle**

Run from the old root:

```powershell
git bundle create ai-nav-fullstack/.repo-backups/pre-root-migration.bundle --all
git bundle verify ai-nav-fullstack/.repo-backups/pre-root-migration.bundle
```

Expected: all refs required by the bundle are reported complete.

### Task 2: Build the root-lifted candidate in isolation

**Files:**
- Create: temporary isolated clone under the operating-system temporary directory
- Modify in candidate: repository history and working tree only

**Interfaces:**
- Consumes: verified bundle and current source branch
- Produces: candidate branch whose root is the former `ai-nav-fullstack/` prefix

- [ ] **Step 1: Clone the bundle into an isolated directory**

Run:

```powershell
git clone .repo-backups/pre-root-migration.bundle <temporary-candidate-directory>
```

Expected: clone succeeds without network access.

- [ ] **Step 2: Extract the project prefix**

Run in the candidate:

```powershell
git subtree split --prefix=ai-nav-fullstack <source-commit> -b repository-root-candidate
git switch repository-root-candidate
```

Expected: `git ls-tree --name-only HEAD` lists `backend`, `frontend`, `docs`, and other project-root entries, and does not list `ai-nav-fullstack`, `agent`, `assets`, or `design`.

- [ ] **Step 3: Apply the tracked workspace delta**

Create a binary-safe diff from the old repository and apply it inside the candidate:

```powershell
git diff --binary <source-commit> -- ai-nav-fullstack | git apply --directory=<candidate-root>
```

Before application, rewrite only the leading `ai-nav-fullstack/` path prefix in patch headers. Do not read file contents for `.env` paths and do not include ignored files.

Expected: candidate tracked files match the current tracked workspace state.

- [ ] **Step 4: Copy approved untracked source and documentation**

Copy only untracked paths reviewed through `git status --short` and `git check-ignore`. Exclude `.tmp_ci.txt`, `.tmp_push_ci.txt`, `.repo-backups/`, `release/`, runtime databases, real environment files, credentials, and generated evidence.

Expected: intended deployment documentation and this plan are present; excluded runtime artifacts are absent.

### Task 3: Restore repository-level automation at the correct root

**Files:**
- Create: `.github/workflows/ai-nav-foundation-ci.yml`
- Modify: workflow path filters, script paths, and working directories

**Interfaces:**
- Consumes: the existing parent-repository workflow
- Produces: root-relative CI for the extracted project

- [ ] **Step 1: Copy the existing workflow into the candidate**

Copy `.github/workflows/ai-nav-foundation-ci.yml` from the source commit into the candidate.

Expected: the workflow is now owned by the project repository.

- [ ] **Step 2: Remove the obsolete project prefix**

Replace workflow-only path references beginning with `ai-nav-fullstack/` by repository-root-relative paths. Remove path filters for sibling projects.

Expected: no workflow command or filter refers to the former wrapper directory.

- [ ] **Step 3: Validate workflow paths**

Run:

```powershell
git grep -n "ai-nav-fullstack/" -- .github/workflows
```

Expected: no matches.

### Task 4: Verify candidate integrity and project gates

**Files:**
- Create in candidate: sanitized verification outputs only when existing scripts require them

**Interfaces:**
- Consumes: complete candidate working tree
- Produces: evidence that repository scope, secrets, syntax, and project gates are acceptable

- [ ] **Step 1: Verify repository scope**

Run:

```powershell
git status --short
git ls-files
git rev-parse --show-toplevel
```

Expected: the candidate root is the project root; no sibling-project or excluded runtime path is tracked.

- [ ] **Step 2: Scan tracked filenames and content for prohibited material**

Use `git ls-files` and the repository's existing secret-scanning or quality scripts. Do not open or print real environment files.

Expected: no real `.env`, private key, access token, cookie, production database, or generated release artifact is tracked.

- [ ] **Step 3: Run the critical and full-function gates**

Run the repository's documented foundation, quality, Agent, and deployment validation commands with test-only configuration.

Expected: locally runnable gates pass with newly recorded numbers; external production checks remain explicitly unverified.

- [ ] **Step 4: Commit the candidate**

Run:

```powershell
git add --all
git commit -m "chore: make ai-nav-fullstack the repository root"
```

Expected: a clean candidate branch with a single migration commit on top of the extracted history.

### Task 5: Publish safely and switch repository ownership

**Files:**
- Modify remotely: candidate branch first; default branch only after confirmation
- Create locally: `.git` inside `D:\Web期末作业\ai-nav2\ai-nav-fullstack`

**Interfaces:**
- Consumes: verified candidate commit
- Produces: GitHub repository and local checkout rooted at `ai-nav-fullstack`

- [ ] **Step 1: Push the non-destructive candidate branch**

Run:

```powershell
git push origin repository-root-candidate
```

Expected: GitHub displays project files directly at the candidate branch root while `master` remains unchanged.

- [ ] **Step 2: Obtain explicit confirmation for default-branch replacement**

Compare the candidate tree, Actions configuration, and verification results with the existing remote. Do not proceed on ambiguous or failed evidence.

- [ ] **Step 3: Replace the default branch only after confirmation**

Use a lease-protected force update for the exact verified candidate commit, then handle obsolete branches and PRs deliberately.

Expected: `master` points to the verified root-lifted history and no unreviewed remote ref is changed.

- [ ] **Step 4: Recreate the local checkout boundary**

After preserving the old parent repository and current workspace, make `D:\Web期末作业\ai-nav2\ai-nav-fullstack` an independent clone of the corrected remote and verify:

```powershell
git rev-parse --show-toplevel
```

Expected: output is exactly `D:\Web期末作业\ai-nav2\ai-nav-fullstack`.
