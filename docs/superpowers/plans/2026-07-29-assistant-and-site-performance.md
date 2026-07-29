# Assistant and Site Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复没有确定性回答的助手示例，并在保持 HTTP 子路径和安全边界的前提下优化助手与全站加载/交互。

**Architecture:** 保留当前原生 HTML/CSS/ES modules 与 FastAPI/Nginx 部署，只解除认证、导航、页面数据之间的串行等待。浏览器高频更新通过帧合并，异步查询通过取消与版本号保持最新，静态缓存仅用于内容指纹资源。

**Tech Stack:** HTML5, CSS, native ES modules, Node test runner, Python unittest, FastAPI, Nginx, PowerShell deployment tooling.

## Execution status (2026-07-29)

- Tasks 1–5 are implemented. The complete Node frontend set passed 73/73 and
  `scripts/verify-frontend.ps1` passed 58/58 plus JavaScript syntax and
  whitespace checks.
- Python portions and the complete repository gates in Task 6 now pass in the
  original worktree: 259 Python tests, 86.4% branch coverage, Ruff and
  dependency audit, Foundation, and HTTP deployment groups
  49/8/74/27/71/22/7.
- Local 8088 smoke and Playwright functional verification pass. Task 6 Git,
  current-release server deployment, post-deploy public probes and same-host
  cold/warm cache comparison remain `NOT RUN`. See
  `docs/05-quality/audits/http-test-assistant-site-performance-20260729.md`.

## Global Constraints

- 不读取、打印、移动或修改真实 `.env`。
- 不调用真实 Provider，不产生付费或生产流量。
- 不覆盖、回滚或批量暂存工作区已有改动。
- HTTP 测试部署与生产发布分别结论；生产保持 `NO-GO`。
- 不引入新 npm/pip 依赖、前端框架、打包器或 Service Worker。
- 页面和 API 的发布一致性优先于未经指纹的长缓存。

---

### Task 1: Deterministic example contract

**Files:**
- Modify: `frontend/assistant.html`
- Modify: `tests/test_agent_frontend.mjs`
- Modify: `tests/test_agent_services.py`

**Interfaces:**
- Consumes: `classify_intent("RAG 怎么学？")`, `agent_retrieval_query(...)`
- Produces: 首个建议稳定触发 `learning_plan`，查询词为 `RAG`

- [ ] **Step 1: Write the failing tests**

新增断言：首个 `data-prompt` 为 `RAG 怎么学？`；后端返回
`learning_plan`、RAG 站内链接，且不调用 Tools/Workflow。

- [ ] **Step 2: Run tests and confirm the old prompt fails**

Run: `node --test tests/test_agent_frontend.mjs`

Run: `python -m unittest tests.test_agent_services`

- [ ] **Step 3: Replace only the unsupported prompt**

保留四张建议卡的位置和其他文案，只把第一张改为 `RAG 怎么学？`。

- [ ] **Step 4: Re-run both focused tests**

Expected: zero failures.

### Task 2: Frame-batched assistant rendering

**Files:**
- Modify: `frontend/assets/js/page-shell.js`
- Modify: `frontend/assets/js/assistant-page.js`
- Create: `tests/test_frontend_performance.mjs`

**Interfaces:**
- Produces: `createFrameBuffer(render, options)` and `frameThrottle(callback, schedule)`
- Consumes: SSE `response.answer.delta`

- [ ] **Step 1: Test frame coalescing and forced flush**

使用可控 scheduler 推入 100 个 delta，断言只排一个 frame、文本顺序完整；
调用 `flush()` 时取消待处理 frame 并立即输出。

- [ ] **Step 2: Confirm the helper imports fail before implementation**

Run: `node --test tests/test_frontend_performance.mjs`

- [ ] **Step 3: Implement the two small schedulers and wire SSE**

每帧最多一次 `textContent`/scroll 更新；在 stream `finally` 强制 flush。

- [ ] **Step 4: Re-run the performance and Agent frontend tests**

Expected: zero failures.

### Task 3: Non-blocking page shell and bounded async refresh

**Files:**
- Modify: `frontend/assets/js/auth-ui.js`
- Modify: `frontend/assets/js/page-shell.js`
- Modify: `frontend/assets/js/home-page.js`
- Modify: `frontend/assets/js/learn-page.js`
- Modify: `frontend/assets/js/learn-node-page.js`
- Modify: `frontend/assets/js/tools-entry.js`
- Modify: `frontend/assets/js/v2-api.js`
- Modify: `frontend/assets/js/assistant-page.js`
- Modify: `tests/test_auth_ui.mjs`
- Modify: `tests/test_frontend_entries.mjs`

**Interfaces:**
- `initAuthUI(): Promise<User|null>` remains compatible.
- `initPageShell(activeCode): Promise<[unknown, User|null]>` still exposes completion,
  but public page entries no longer await it.

- [ ] **Step 1: Add tests for immediate event binding and non-blocking entries**

断言 runtime/auth 并行、事件只绑定一次、公开入口不含顶层
`await initPageShell`；设置页继续等待 `initAuthUI`。

- [ ] **Step 2: Run focused tests and verify failure**

Run: `node --test tests/test_auth_ui.mjs tests/test_frontend_entries.mjs`

- [ ] **Step 3: Implement idempotent auth bootstrap**

先渲染 logged-out 占位并绑定事件，再并行请求 capabilities 与当前会话。

- [ ] **Step 4: Remove public-entry top-level shell waits**

使用 `void initPageShell(...).catch(...)`，公开数据和交互立即启动。

- [ ] **Step 5: Make answer list refresh background and scoped**

按 `ags_`/`agl_` 只刷新受影响列表；递增版本号拒绝迟到响应。

- [ ] **Step 6: Re-run all focused Node tests**

Expected: zero failures.

### Task 4: Search, learning and long-page rendering

**Files:**
- Modify: `frontend/assets/js/site-search.js`
- Modify: `frontend/assets/js/learning-pages.js`
- Modify: `frontend/assets/css/accessibility.css`
- Modify: `frontend/assets/js/home-page.js`
- Modify: `tests/test_frontend_performance.mjs`
- Modify: `tests/test_learning_frontend.mjs`

**Interfaces:**
- Search uses `AbortSignal` through existing `apiGet(path, params, options)`.
- Learning loaders retain their independent fallback UI.

- [ ] **Step 1: Add failing behavior/contract tests**

覆盖 180 ms debounce、AbortController/sequence、`Promise.all` learning hydration、
rAF scroll batching and content visibility selectors.

- [ ] **Step 2: Confirm tests fail for missing behavior**

Run: `node --test tests/test_frontend_performance.mjs tests/test_learning_frontend.mjs`

- [ ] **Step 3: Implement minimum changes**

不改搜索排序和 Learning API，只改变调度与并发。

- [ ] **Step 4: Re-run focused tests**

Expected: zero failures.

### Task 5: Critical resource discovery and delivery

**Files:**
- Create: `frontend/assets/img/brand-mark.<sha8>.svg`
- Modify: six `frontend/*.html` pages
- Modify: `frontend/assets/js/auth-ui.js`
- Modify: `deploy/http-test/nginx/ai-nav.conf`
- Modify: `tests/test_frontend_entries.mjs`
- Modify: `tests/test_http_static_revalidation.py`
- Modify: `tests/test_http_test_overlay.py`

**Interfaces:**
- HTML discovers page entry using `<link rel="modulepreload">`.
- Only the fingerprint SVG receives `public, max-age=31536000, immutable`.
- Generic `/StarChart-AI/` remains `no-cache`.

- [ ] **Step 1: Add failing tests for asset size/reference and cache boundary**

断言所有页面预加载自己的入口、不再引用 `logo.png`、指纹 SVG 小于 4 KiB；
Nginx generic response remains `no-cache` and exact SVG is immutable.

- [ ] **Step 2: Run Node/Python focused tests and confirm failure**

Run: `node --test tests/test_frontend_entries.mjs`

Run: `python -m unittest tests.test_http_static_revalidation tests.test_http_test_overlay`

- [ ] **Step 3: Add SVG, preload links and Nginx gzip/cache rules**

gzip 只增加文本类型；不改变 API 限流、代理超时或 Provider 路由。

- [ ] **Step 4: Re-run focused tests**

Expected: zero failures.

### Task 6: Gates, review, deploy and online verification

**Files:**
- Modify: deployment audit/runbook/index documents only with measured results

- [ ] **Step 1: Run focused Node tests and syntax checks**

Run all changed MJS tests plus `node --check` on changed JS.

- [ ] **Step 2: Run project gates**

Run `verify-agent.ps1`, `verify-foundation.ps1`, `verify-quality.ps1`,
`verify-http-test-deployment.ps1`, release validation and `git diff --check`.

- [ ] **Step 3: Review exact diff and commit only task files**

Do not stage unrelated dirty files.

- [ ] **Step 4: Build immutable release and deploy to the approved HTTP test host**

Validate archive, copy release, switch `/opt/starchart-ai/current`, install tested
Nginx overlay, run `nginx -t`, restart only `starchart-ai-http-test`.

- [ ] **Step 5: Re-run online functional/performance probes**

Verify six pages, module/SVG headers, runtime, navigation, capabilities and one
sanitized deterministic guest prompt. Compare same curl/Chrome conditions with
the captured baseline.

- [ ] **Step 6: Update evidence and final conclusions**

Record current release and measured counts; deterministic HTTP may be `GO` only
with fresh evidence. Production remains `NO-GO`.
