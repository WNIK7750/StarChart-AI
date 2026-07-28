# Git 提交就绪报告与执行交接

> 状态：**允许创建本地 Git 基线提交；禁止据此直接生产发布**  
> 日期：2026-07-25  
> 用途：交给另一名 AI 执行暂存、复核和提交  
> 仓库根目录：`D:/Web期末作业/ai-nav2`  
> 项目目录：`D:/Web期末作业/ai-nav2/ai-nav-fullstack`  
> 当前分支：`agent/sync-agent-foundation-cn`  
> 当前 HEAD：`45238d4e1054ff5240bb924f78210cbb2bbd33d0`  
> 执行限制：只创建本地提交，不 push、不打 tag、不创建 Release、不部署

---

## 1. 最终判断

### 1.1 Git 提交判断

**GO：可以创建一个新的本地 Git 提交。**

理由：

- 当前本地整改候选已经通过独立复验；
- 当前代码重新通过统一质量门禁；
- 代码、测试、迁移、文档和机器证据是同一份互相依赖的已验证快照；
- 真实 `.env`、本地 SQLite、虚拟环境、上传目录和覆盖率临时文件均被 Git 忽略；
- 发布包 allowlist 校验通过；
- 工作树变更范围只涉及本项目和本项目的 CI 工作流；
- 当前没有已暂存文件，执行 AI 可以从干净的暂存区开始复核。

### 1.2 生产发布判断

**NO-GO：本次 Git 提交不能解释为允许生产发布。**

仍缺：

- 真实邮件/短信账户恢复发送服务；
- Provider 合规、数据保留/训练政策和用户告知；
- 阿里云百炼受控真实调用；
- 上海服务器到北京业务空间的生产网络；
- 真实费用硬限制、容量和告警；
- 生产备份恢复和回滚演练；
- 外部责任人签收。

权威清单：

- `ai-nav-fullstack/docs/04-operations/production-external-signoff-checklist.md`
- `ai-nav-fullstack/docs/05-quality/audits/full-project-remediation-verification-report.md`

---

## 2. 当前 Git 基线

| 项目 | 当前值 |
| --- | --- |
| 仓库根目录 | `D:/Web期末作业/ai-nav2` |
| 项目目录 | `ai-nav-fullstack/` |
| 分支 | `agent/sync-agent-foundation-cn` |
| HEAD | `45238d4e1054ff5240bb924f78210cbb2bbd33d0` |
| HEAD 摘要 | `test: 适配不同环境的密码升级验证` |
| 已暂存变更 | 0 |
| 已修改路径 | 60 |
| 已删除旧路径 | 43 |
| 未跟踪新路径/文件 | 138 |
| 具体状态条目合计 | 241 |

注意：未跟踪数量使用 `git status --porcelain=v1 -uall` 统计。普通
`git status --short` 会把未跟踪目录折叠，不能用于核对真实文件数量。

当前 43 个删除路径主要来自文档目录治理。原 `docs/` 根目录、`docs/users-baseline/`
等文件已经迁入：

- `docs/00-index/`
- `docs/01-overview/`
- `docs/02-architecture/`
- `docs/03-domains/`
- `docs/04-operations/`
- `docs/05-quality/`
- `docs/06-evidence/`
- `docs/07-prompts/`

暂存后必须使用 rename detection 复核这些移动；不要只看到 `D` 就恢复旧文件，也不要同时
保留旧、新两份重复文档。

---

## 3. 本提交应包含的范围

### 3.1 唯一允许的仓库范围

1. `.github/workflows/ai-nav-foundation-ci.yml`
2. `ai-nav-fullstack/**`

仓库中不存在其它待提交的兄弟项目变更。若执行时发现上述范围外的新变更，立即停止并报告。

### 3.2 应包含的成果

- Platform/Core 安全配置、数据库连接关闭和安全响应头；
- FastAPI/Starlette/Pillow/multipart 等锁定依赖；
- Agent Provider、编排、治理、SSE、短期会话和长期对话；
- Agent 迁移 018—020；
- 账户恢复新边界及一次性恢复凭据；
- Access Token 内存化和 Refresh Cookie 恢复；
- 头像、multipart、Range 等输入安全；
- Platform、Tools、Users、Privacy、Assets、Agent 字段级响应 DTO；
- 84/84 JSON 操作响应契约及内部字段过滤回归；
- Frontend、Users、Agent 和 HTTP 边界测试；
- Ruff、依赖审计、覆盖率和发布包门禁；
- 文档目录治理；
- 当前审计、复验、机器证据和外部签收清单；
- `.env.example` 与 `production.env.example` 无密钥模板；
- 本 Git 提交交接报告。

### 3.3 应保留的删除

旧文档路径的删除是目录治理的一部分。暂存后，如果 Git 识别为 rename/copy，属于预期。
执行 AI 不得：

- 恢复旧扁平文档目录；
- 同时提交旧路径和新路径的重复副本；
- 删除新 `docs/00-index` 至 `docs/07-prompts` 目录；
-修改机器证据中的数字来迎合旧报告。

---

## 4. 严禁提交的内容

以下任一项进入暂存区都必须停止：

- `.env`
- 任何真实 API Key、应用密钥、Token、Cookie 或 Authorization 值
- `database/ai_nav.sqlite3`
- 其它 `*.sqlite`、`*.sqlite3`、本地数据库副本
- `.venv/`
- `node_modules/`
- `uploads/`
- `__pycache__/`、`*.pyc`
- `.coverage`、`coverage.xml`、临时 HTML coverage
- 本地服务器 `*.log`
- 临时恢复文件、数据库 WAL/SHM
- 未经 allowlist 生成的 zip、7z、tar 等归档
- Cloudflare Quick Tunnel 地址或临时进程输出
- Provider 原始 request/response
- 真实用户输入、联系方式或可识别设备信息

以下文件名带 `env` 但属于允许内容：

- `ai-nav-fullstack/.env.example`
- `ai-nav-fullstack/production.env.example`

它们必须保持无真实值。

当前忽略检查已经确认：

| 路径 | 状态 |
| --- | --- |
| `.env` | ignored |
| `database/ai_nav.sqlite3` | ignored |
| `.venv/` | ignored |
| `uploads/` | ignored |
| `.coverage` | ignored |
| `coverage.xml` | ignored |

---

## 5. 为什么建议一个原子提交

默认建议创建一个提交，而不是机械拆成多个提交。

原因：

- 响应 DTO、Router、OpenAPI、前端消费者和契约测试必须同步；
- 认证令牌边界同时影响后端 Cookie、前端内存状态和 Node 测试；
- 文档移动同时修改脚本、CI、README 和机器证据路径；
- 迁移、Agent 会话实现、隐私导出/删除测试属于同一可恢复数据边界；
- 当前 176/176、34/34 和 85.9% 是完整组合的验证结果；
- 任意拆分可能生成无法独立通过门禁的中间提交。

建议提交主题：

```text
feat: establish audited full-stack remediation baseline
```

建议提交正文：

```text
- complete provider, streaming, session and long-conversation boundaries
- harden authentication, recovery, input and production configuration
- replace broad JSON responses with field-level domain DTOs
- add quality, security, coverage and release-package gates
- reorganize audit documentation and preserve machine evidence
```

不要 amend 当前 HEAD；创建一个新提交。

如果项目负责人坚持拆分，必须在新分支中按每个提交分别复跑全部门禁；未经逐提交复验，不要
把当前总体验证数字引用为中间提交的证据。

---

## 6. 执行 AI 的强制步骤

### 步骤 1：确认上下文

在 Windows 11 PowerShell 中：

```powershell
Set-Location -LiteralPath "D:\Web期末作业\ai-nav2"
git branch --show-current
git rev-parse HEAD
git status --short
git diff --cached --name-status
```

预期：

- 分支为 `agent/sync-agent-foundation-cn`；
- HEAD 为 `45238d4e1054ff5240bb924f78210cbb2bbd33d0`；
- 暂存区为空。

若 HEAD、分支或暂存区不同，停止并报告，不要自行 reset、stash 或覆盖。

### 步骤 2：复跑当前门禁

```powershell
Set-Location -LiteralPath "D:\Web期末作业\ai-nav2\ai-nav-fullstack"

& "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\verify-quality.ps1"

& "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\verify-foundation.ps1"

& "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\verify-agent.ps1"
```

预期关键结果：

- 176/176 Python；
- 34/34 Node；
- 36/36 JavaScript 语法；
- 85.9% 分支覆盖率，不低于 84%；
- Ruff 0；
- 依赖漏洞 0；
- Foundation 和 Agent 通过；
- `git diff --check` 通过。

门禁会设置 `AI_NAV_DISABLE_DOTENV=1`，不得读取真实 `.env`。

### 步骤 3：验证发布 allowlist

```powershell
& "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -NoProfile -ExecutionPolicy Bypass `
  -File ".\scripts\build-release-package.ps1" `
  -ValidateOnly
```

预期：

- `passed: true`
- `forbiddenCount: 0`

本报告加入后重新验证的当前值仍为 `fileCount: 347`、`forbiddenCount: 0`。执行 AI 应以
执行时的实际文件树为准；如果数量变化，必须解释新增/删除内容，不能为追求旧数字删除本报告。

### 步骤 4：从仓库根目录精确暂存

```powershell
Set-Location -LiteralPath "D:\Web期末作业\ai-nav2"

git add -A -- `
  ".github/workflows/ai-nav-foundation-ci.yml" `
  "ai-nav-fullstack"
```

不要使用无路径限制的 `git add -A`，即使当前没有其它兄弟项目变更。

### 步骤 5：检查暂存范围

```powershell
$staged = git diff --cached --name-only
$unexpected = $staged | Where-Object {
  $_ -ne ".github/workflows/ai-nav-foundation-ci.yml" -and
  $_ -notlike "ai-nav-fullstack/*"
}
if ($unexpected) {
  $unexpected
  throw "暂存区包含项目范围外文件"
}

git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
git diff --cached --find-renames --summary
```

需要人工/AI 阅读：

- 所有 `D` 是否有对应的新分类路径或确属淘汰；
- 三个迁移 018—020 是否存在；
- DTO、Router 和测试是否同时存在；
- README、文档地图、整改报告和机器证据路径是否一致；
- CI 工作流是否只有本项目相关门禁。

### 步骤 6：检查禁入路径

```powershell
$staged = git diff --cached --name-only
$forbidden = $staged | Where-Object {
  $_ -match '(^|/)\.env$' -or
  $_ -match '\.(sqlite|sqlite3|db|pyc|log|zip|7z|tar)$' -or
  $_ -match '(^|/)(\.venv|node_modules|uploads|__pycache__)(/|$)' -or
  $_ -match '(^|/)\.coverage$' -or
  $_ -match '(^|/)coverage\.xml$'
}
if ($forbidden) {
  $forbidden
  throw "暂存区包含禁入产物"
}
```

随后人工打开并确认：

- `ai-nav-fullstack/.env.example`
- `ai-nav-fullstack/production.env.example`

只确认占位符和空值，不读取真实 `.env`。

### 步骤 7：创建本地提交

只有全部检查通过后：

```powershell
git commit `
  -m "feat: establish audited full-stack remediation baseline" `
  -m "Complete Provider, streaming, session and long-conversation boundaries." `
  -m "Harden authentication, recovery, input and production configuration." `
  -m "Replace broad JSON responses with field-level DTOs and add quality gates." `
  -m "Reorganize audit documentation and preserve machine evidence."
```

### 步骤 8：提交后核对

```powershell
git status --short
git show --stat --oneline --decorate HEAD
git log -2 --oneline
```

预期：

- 工作树为空；
- HEAD 是新提交；
- 上一个提交仍是 `45238d4`；
- 没有自动 push。

如果提交后工作树不为空，先列出剩余文件并报告，不要追加第二个“补漏提交”，也不要 amend，
除非项目负责人明确确认。

---

## 7. 禁止操作

执行 AI 不得：

- `git reset --hard`
- `git clean`
- `git checkout -- <path>`
- 无审阅地恢复 43 个旧文档路径
- 删除未跟踪的新实现
- amend `45238d4`
- 自动 rebase 或 merge
- 自动 push
- 创建 tag、Release 或部署
- 读取真实 `.env`
- 调用真实 Provider
- 为让工作树变干净而提交数据库、日志或临时文件
- 把“本地提交成功”改写为“生产发布 GO”

如果暂存有误，允许使用不改变工作树文件的方式撤销暂存：

```powershell
git restore --staged -- `
  ".github/workflows/ai-nav-foundation-ci.yml" `
  "ai-nav-fullstack"
```

撤销暂存后重新核对，不要丢弃工作树内容。

---

## 8. 提交执行后的回报格式

执行 AI 应返回：

```text
提交结果：成功 / 未执行
分支：
新提交 SHA：
提交标题：
提交文件数量：
提交后工作树：
质量门禁：
Foundation 门禁：
Agent 门禁：
发布 allowlist：
禁入文件：
是否 push：否
生产发布判断：NO-GO
异常或剩余文件：
```

如果失败，必须附上失败步骤和原始错误摘要，但不得附密钥、Token、Provider body 或用户数据。

---

## 9. 本报告生成时的证据

- `scripts/verify-quality.ps1`：通过；
- Python：176/176；
- Node：34/34；
- JavaScript 语法：36/36；
- 分支覆盖率：85.9%；
- Ruff：0；
- 依赖漏洞：0；
- `git diff --check`：通过；
- 发布 allowlist：本报告加入后重新验证为 347 个文件、禁入产物 0；
- 当前暂存区：空；
- 当前范围外工作树变更：0；
- 真实 `.env`：未读取；
- 真实 Provider：未调用；
- Git 提交：未由本报告生成者执行。

最终依据仍是执行 AI 在实际暂存前后重新运行的结果。
