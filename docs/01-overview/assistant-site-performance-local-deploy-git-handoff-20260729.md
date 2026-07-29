# 助手与全站性能：本地部署及 Git 执行交接

> 用途：把 2026-07-29 助手、认证、Learning 与全站性能整改交给新对话继续执行。
> 状态：前端、Python 全门禁、本地 smoke 与浏览器验收已完成；Git 提交、CI 与
> 当前性能候选的 HTTP 服务器部署尚未完成。
> 日期：2026-07-29。
> 权威性：当前代码和本次重新运行的测试优先于本文；本文不得覆盖服务器事实。

本文不记录测试账号、密码、Token、Cookie、真实 `.env`、Provider 请求或回答正文。

## 1. 新对话的首要入口

新对话应进入：

```text
D:\Web期末作业\ai-nav2\ai-nav-fullstack
```

然后依次完整阅读：

1. `docs/01-overview/assistant-site-performance-local-deploy-git-handoff-20260729.md`
2. `docs/00-index/http-test-deployment-file-index.md`
3. `docs/05-quality/audits/http-test-assistant-site-performance-20260729.md`
4. `docs/superpowers/specs/2026-07-29-assistant-and-site-performance-design.md`
5. `docs/superpowers/plans/2026-07-29-assistant-and-site-performance.md`
6. `docs/05-quality/audits/git-http-privacy-audit.md`
7. `docs/04-operations/deployment/http-test-deployment-runbook.md`
8. `docs/04-operations/deployment/http-test-deployment-troubleshooting.md`

不要继续执行
`docs/05-quality/audits/git-commit-readiness-handoff.md` 中的暂存命令；该文件已经
明确标记为历史快照。

## 2. 当前 Git 与工作区事实

### 2.1 应使用的真实工作目录

原工作目录：

```text
D:\Web期末作业\ai-nav2\ai-nav-fullstack
```

当前分支：

```text
agent/fix-http-subpath-navigation
```

当前 HEAD：

```text
96ea113 fix: keep assistant settings access in context
```

默认分支：

```text
master -> 3c0b1fd chore: make ai-nav-fullstack the repository root
origin/master 同步到该提交
```

远端：

```text
origin https://github.com/WNIK7750/StarChart-AI.git
```

本次交接生成时所在的 Codex linked worktree 为：

```text
C:\Users\LEGION\.codex\worktrees\f11f\ai-nav-fullstack
```

该 linked worktree 是 detached HEAD，虽然当前承载了相同未提交修改，但不得直接
从 detached HEAD 推送。Git 提交和 push 优先回到原工作目录及上述命名分支执行。

### 2.2 当前工作树

当前包含大量已修改和未跟踪文件，暂存区是否为空必须重新检查。不得执行：

- `git reset --hard`
- `git checkout -- <path>`
- 未复核前的 `git add -A`
- force push
- 覆盖、回滚或丢弃现有工作区修改

新对话先运行：

```powershell
Set-Location -LiteralPath "D:\Web期末作业\ai-nav2\ai-nav-fullstack"
git branch --show-current
git rev-parse HEAD
git status --short
git diff --cached --name-status
```

若分支、HEAD 或暂存区与本文不同，先报告差异，不得自行 reset 或 stash。

## 3. 已完成的实现

### 3.1 助手

- 首个建议问题已从没有确定性规则的比较问题改为“RAG 怎么学？”。
- 该问题对应现有 `learning_plan` 路径，Python 契约测试已补在
  `tests/test_agent_services.py`。
- SSE delta 使用动画帧缓冲，结束、中止和异常路径强制 flush。
- 短期、长期会话列表分别维护请求版本并批量挂载 DOM。
- 会话全量刷新改为 `Promise.allSettled`；长期列表失败不会再误禁用新短会话。
- 回答完成后只后台刷新受影响的会话类型，不阻塞输入恢复。

关键文件：

- `frontend/assistant.html`
- `frontend/assets/js/assistant-page.js`
- `frontend/assets/js/page-shell.js`
- `tests/test_agent_frontend.mjs`
- `tests/test_frontend_performance.mjs`
- `tests/test_interaction_performance.mjs`
- `tests/test_agent_services.py`

### 3.2 认证与 Learning

- 认证能力和会话恢复并行，认证事件只绑定一次。
- 登录成功保存 token 后，在第一次后续 `await` 前立即启动新认证刷新，使旧启动
  请求失效，避免旧匿名结果覆盖新登录。
- Learning 公开 roadmap 和资源不等待登录恢复。
- 初始登录恢复和页内登录都会补齐进度、dashboard、收藏和偏好。
- 身份切换复用 `AssistantSessionEpoch`；退出或换账号会使旧水合失效并清理旧
  账号个人学习 DOM。
- dashboard 和偏好缓存按当前 access token 隔离。

关键文件：

- `frontend/assets/js/auth-ui.js`
- `frontend/assets/js/learning-pages.js`
- `frontend/assets/js/learning-state.js`
- `frontend/assets/js/user-preference-consumers.js`
- `frontend/assets/js/learn-page.js`
- `frontend/assets/js/learn-node-page.js`
- `tests/test_auth_ui.mjs`
- `tests/test_learning_frontend.mjs`

### 3.3 全站加载与交互

- 首页、学习、节点、工具和助手公开内容不再被页面壳层串行阻塞。
- 搜索使用 180 ms 去抖、`AbortController` 和序号拒绝迟到结果。
- navbar、首页进度、工具页滚动、spotlight 和工具卡坐标按动画帧合并。
- 屏外长区块使用 `content-visibility:auto`；没有对整个动态工具目录使用，
  避免滚动位置跳变。
- 设置页先绑定主交互，再后台加载次要账号区域。
- 六个页面通过 `modulepreload` 提前发现入口模块。
- 原关键路径的 1,229,532 B PNG 已替换为 352 B 指纹 SVG：
  `frontend/assets/img/brand-mark.62793ed5.svg`。
- Nginx 对文本资源启用 gzip；只有该指纹 SVG 使用一年 immutable，泛路径和
  未指纹 HTML/JS/CSS 继续 `no-cache`。
- HTTP 发布门禁现在把未跟踪发布文件视为 dirty，禁止把非 commit 内容伪装成
  HEAD release。

## 4. 本轮验证证据

2026-07-29 在原工作目录重新运行的结果：

| 命令 | 真实结果 |
| --- | --- |
| `node --test tests/*.mjs` | 73 passed，0 failed，270.9565 ms |
| `scripts/verify-frontend.ps1` | 58 passed，0 failed，177.5433 ms |
| `scripts/verify-quality.ps1` | 259 项 Python 测试通过；分支覆盖率 86.4%；Ruff 和依赖审计通过；发布选择 367/0/10 |
| `scripts/verify-foundation.ps1` | 通过 |
| `scripts/verify-http-test-deployment.ps1` | 49/8/74/27/72/22/7 全部通过 |
| 目标 JavaScript 语法 | 通过 |
| `git diff --check` | 通过 |
| 指纹 SVG | 352 B，SHA-256 前缀 `62793ed5` |
| 8088 只读 smoke | 清单中的 10 个页面、资源和 API 全部返回 200 |
| 本地 Playwright | 桌面五页与 390×844 助手页通过；游客问答/草稿/设置门禁和合成账号短会话问答通过 |

这些数字属于产生它们时的原工作目录。同步文档后的最终提交前仍须重新运行
`git diff --check` 和相应文档/秘密扫描，不能把数字套用到后续代码修改。

仍不得写成通过：

- 当前性能候选的 SSH 部署、服务器 `nginx -t`、systemd、线上 smoke；
- 同一公网环境下的冷/暖缓存性能对比；
- 真实 Provider、HTTPS、容量、备份恢复、回滚演练和生产签收。

## 5. 本地运行实例

用户截图显示原工作目录的 `.venv` 已可用，Uvicorn 正运行于：

```text
http://127.0.0.1:8088/
```

本轮确认 8088 原先没有监听，随后使用原工作目录 `.venv` 启动唯一实例。首页、
五个业务页面、指纹 SVG、导航、公开运行能力和 Agent 能力共 10 个清单路径均
返回 200，本轮耗时约 3.2–233.3 ms。

普通 8088 开发档按策略公开 `guestChat=false`。为了不改源码、不读取真实
`.env`，游客 deterministic 浏览器复验使用临时外部数据库启动隔离 `http_test`
实例，并在 Playwright 中模拟 Nginx 的 `/StarChart-AI` 前缀剥离；登录态复验
使用临时 `test` 实例和纯合成账号。两个临时实例与数据库已在复验后删除。该证据
不能替代真实服务器 Nginx、systemd 或发布后公网验证。

新对话不得直接再启动第二个 8088 实例。先检查：

```powershell
Get-NetTCPConnection -LocalPort 8088 -State Listen -ErrorAction SilentlyContinue
```

若已有监听，复用它进行只读 smoke；若没有，再按 `README.md`/`start.ps1`
启动。不要读取或打印真实 `.env`。

## 6. 后续必须执行的顺序

阶段 A 与阶段 B 已在本轮完成；以下步骤保留为后续代码变化时的复验清单。当前
从阶段 C 文档同步与阶段 D Git 审计继续，阶段 E 仍受提交固定、CI 和服务器授权
约束。

### 阶段 A：确认本地源码和运行实例一致

1. 在原工作目录核对分支、HEAD、暂存区和工作树。
2. 确认 8088 是否正在监听，避免重复进程。
3. 对下列本地路径重新运行只读 smoke，并记录本次真实状态和耗时：

```text
/
/assistant.html
/learn.html
/learn-node.html?slug=rag
/tools.html
/settings.html
/assets/img/brand-mark.62793ed5.svg
/api/v1/navigation
/api/v1/runtime/public
/api/v1/agent/capabilities
```

4. 浏览器人工复核关键全流程：
   - 游客助手建议“RAG 怎么学？”可得到确定性站内学习回答；
   - 游客普通对话、短/长记忆和工作流草稿符合既有 HTTP 规范；
   - 登录后短期、长期会话可加载，新建、发送和列表失败路径互不连带；
   - 未登录点击助手页设置只在原页提示登录；
   - 已登录点击设置进入设置页，不出现乱码或二次错误跳转；
   - 学习页刷新恢复登录、页内登录和退出后的个人状态边界正确；
   - 首页、学习、工具、助手、设置之间跳转没有明显冻结或错误重定向。

本地验收不得调用真实 Provider或产生付费流量；使用 deterministic 测试路径。

### 阶段 B：运行本地门禁

先运行快速门禁：

```powershell
node --test tests/*.mjs
.\scripts\verify-frontend.ps1
git diff --check
```

原工作目录已有 `.venv` 时，再运行项目正式门禁：

```powershell
.\scripts\verify-quality.ps1
.\scripts\verify-foundation.ps1
.\scripts\verify-http-test-deployment.ps1
```

这些脚本若会更新机器证据，更新后必须复核实际差异。不得读取真实 `.env`，不得
调用真实 Provider。若门禁失败，先定位本次真实失败，不得引用历史通过数字。

上述门禁和关键浏览器流程本轮均已通过，“完整仓库本地候选”已更新为 `GO`。
这仍不代表 HTTP 服务器或生产发布通过。

### 阶段 C：同步文档

用本次重新运行的数字更新：

- `docs/05-quality/audits/http-test-assistant-site-performance-20260729.md`
- `docs/00-index/http-test-deployment-file-index.md`
- `docs/00-index/documentation-map.md`
- 本交接文档

必须分别记录：

- 本地源码候选；
- 本地运行实例；
- 当前 HTTP 服务器性能候选；
- 生产发布。

### 阶段 D：Git

本地全部确认后：

1. 复核 `git status --short`、`git diff --stat`、`git diff --check`。
2. 确认没有 `.env`、数据库、`.venv`、上传文件、日志、Token、Cookie、真实
   Provider 内容、临时归档或用户隐私数据进入追踪范围。
3. 使用 `docs/00-index/http-test-deployment-file-index.md` 和
   `docs/05-quality/audits/git-http-privacy-audit.md` 判断每个文件归属。
4. 暂存后必须运行：

```powershell
git diff --cached --name-status
git diff --cached --stat
git diff --cached --check
```

5. 不得在当前 detached Codex worktree 直接 push；应在原工作目录的
   `agent/fix-http-subpath-navigation` 分支提交。
6. 建议提交主题：

```text
perf: optimize assistant and site interactions
```

7. 提交后先 push 该功能分支并观察 GitHub Actions；不要直接 force 更新 master：

```powershell
git push -u origin agent/fix-http-subpath-navigation
```

8. CI 全绿且差异范围正确后，再决定通过 PR 合并到 master。若 CI 失败，使用实际
   日志修复，不要只增大 timeout。

### 阶段 E：服务器

只有 commit 固定、发布包 allowlist/秘密扫描通过且本地门禁通过后，才继续当前
性能候选的 HTTP 测试服务器部署。按 runbook 创建新的不可变 release，执行
`nginx -t`、只重启测试服务、复核旧站和新站，再做同条件公网性能探针。

当前性能候选仍是：

```text
HTTP test: NOT DEPLOYED
Production: NO-GO
```

## 7. 文件范围提示

性能批次直接相关的主要修改包括：

```text
deploy/http-test/nginx/ai-nav.conf
frontend/assets/css/accessibility.css
frontend/assets/img/brand-mark.62793ed5.svg
frontend/assets/js/assistant-page.js
frontend/assets/js/auth-ui.js
frontend/assets/js/home-page.js
frontend/assets/js/learn-node-page.js
frontend/assets/js/learn-page.js
frontend/assets/js/learning-pages.js
frontend/assets/js/learning-state.js
frontend/assets/js/page-shell.js
frontend/assets/js/settings.js
frontend/assets/js/site-search.js
frontend/assets/js/tools-entry.js
frontend/assets/js/tools-page.js
frontend/assets/js/user-preference-consumers.js
frontend/assets/js/v2-api.js
frontend/assistant.html
frontend/index.html
frontend/learn-node.html
frontend/learn.html
frontend/settings.html
frontend/tools.html
scripts/verify-frontend.ps1
scripts/verify-http-test-deployment.ps1
tests/test_agent_frontend.mjs
tests/test_agent_services.py
tests/test_auth_ui.mjs
tests/test_frontend_entries.mjs
tests/test_frontend_performance.mjs
tests/test_http_static_performance.mjs
tests/test_http_static_revalidation.py
tests/test_interaction_performance.mjs
tests/test_learning_frontend.mjs
```

工作树还包含更早部署、隐私和文档批次的修改。不要根据上述列表删除其它修改，
也不要把所有修改自动归类为本性能批次；逐项以文件索引和实际 diff 为准。

## 8. 给新对话的执行提示词

```text
请进入工作区 D:\Web期末作业\ai-nav2\ai-nav-fullstack，完整阅读并严格执行：
docs/01-overview/assistant-site-performance-local-deploy-git-handoff-20260729.md

先使用 docs/00-index/http-test-deployment-file-index.md 路由文件和证据。不要直接
相信历史测试数字；本地 8088 smoke、浏览器流程和 Node/Python 全门禁已在
2026-07-29 本轮通过。若代码继续变化，必须重跑受影响门禁。不得读取或打印真实
.env，不得调用真实 Provider，不得覆盖或回滚已有改动。

当前从精确文件审计、隐私扫描和 Git 继续。Git 范围只允许当前 ai-nav-fullstack
仓库，不得纳入上级目录、兄弟项目、备份或无关工作区内容。Git 操作在原工作目录的
agent/fix-http-subpath-navigation 分支执行，不在 detached Codex worktree
直接 push。先提交并 push 功能分支、观察 CI，再决定是否通过 PR 合并 master。

本地、HTTP 测试服务器和生产发布必须分别给结论；当前性能候选 HTTP 仍是
NOT DEPLOYED，生产仍是 NO-GO。
```
