# AI 知识导航

本目录是 AI 知识导航的当前可运行版本，包含网站页面、业务接口、数据库迁移、自动化测试、Agent 能力和发布审计资料。文档地图见 `docs/00-index/documentation-map.md`，当前独立复验结论见 `docs/05-quality/audits/full-project-remediation-verification-report.md`。

## 当前版本

### 首页与公共页面

- 首页只承担内容展示、搜索和主导航，不读取或展示个人学习情况。
- 主导航统一为“主页、学习、工具、助手”。
- 用户空间提供相同顺序的四项导航，并保留独立退出按钮。
- 页面共享登录状态、错误提示、链接安全、键盘焦点和减少动画支持。

### 学习区

- 知识地图包含学习节点、难度、领域、前置关系、推荐下一步和相关节点。
- 节点页展示主资料、章节目录、建议时长、补充资料和访问类型。
- 登录用户可以记录节点进度、章节完成状态、最近阅读和收藏。
- 匿名阅读记录可在登录后幂等导入，不会自动制造学习进度。
- 公开学习内容不依赖用户登录和 Agent 服务。

### 工具区

- 数据库保存 144 条工具事实，其中 134 条当前公开；其余为归档或非活动记录。
- 支持分类、子分类、搜索、免费优先、最新工具和工作流推荐。
- 多页分类在桌面端使用固定三列四行目录，卡片尺寸和分页器位置保持稳定。
- 移动端改为单列自然滚动，不保留桌面端空位。
- 链接健康状态、最后检查时间和归档状态可通过维护脚本更新。

### 用户空间

- 支持注册、登录、刷新、退出、设备会话查看和其他设备退出。
- 支持用户名、邮箱和手机号登录，手机号会统一为标准格式保存。
- 账号页可修改用户名、邮箱和手机号；联系方式变更要求当前密码。
- 支持头像裁剪上传、公开资料、学习偏好、密保资料和密码修改；密保资料不能授权密码恢复。
- 支持协议同意、撤回、数据导出、注销申请及撤销。
- 支持学习概览、最近阅读、收藏和个人工作流资产。

### Agent

- `POST /api/v1/agent/chat` 返回结构化回答、站内引用和工作流草案。
- Agent 可读取学习内容、工具目录以及用户允许使用的最小上下文。
- 工作流保存必须经过用户确认，并使用幂等键防止重复写入。
- 已完成可替换 Provider、确定性回退、SSE、短期会话、最多 3 个长期对话、成本/并发治理和模型升级评测门禁。
- 真实 Provider 默认关闭；阶段 1 唯一默认模型为 `qwen3.5-flash`，`qwen3.7-plus` 已接配置但升级比例固定为 0%。
- 当前不引入多 Agent、向量库、复杂状态图或跨进程运行态；开发完成证据见 `docs/06-evidence/agent/agent_development_completion_audit.json`。

### 安全与运行

- 数据库使用 20 个增量迁移，并记录迁移校验值。
- 登录具备失败锁定、速率限制、刷新令牌轮换和会话撤销。
- 写操作具备权限校验、审计事件、稳定错误码和请求编号。
- 提供数据库备份、恢复、完整性检查、外键检查和发布演练。

## 目录结构

```text
ai-nav-fullstack/
  backend/                FastAPI 应用与业务功能
  database/               初始结构、基础数据和 20 个迁移
  frontend/               首页、学习、工具、助手和用户空间
  scripts/                验证、基准、备份、巡检和发布演练
  tests/                  Python 与前端契约测试
  docs/                   使用说明、验收记录和 Agent 开发计划
```

## 启动方式

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\run.py
```

本地启用阶段 1 模型前，复制安全模板并只在本机填写：

```powershell
Copy-Item .env.example .env
```

在 `.env` 中填写 `AI_NAV_AGENT_PROVIDER_API_KEY`、北京业务空间地址和允许主机。确认发布清单后，再将 `AI_NAV_AGENT_PROVIDER` 改为 `openai_compatible`、将 `AI_NAV_AGENT_PROVIDER_LIVE_ENABLED` 改为 `1`，并重启后端。真实 `.env` 已被 Git 忽略；部署环境应改用平台密钥管理注入同名变量，系统环境变量优先于 `.env`。

默认地址：`http://127.0.0.1:8088/`

主要页面：

- `index.html`：首页
- `learn.html`：学习路线
- `learn-node.html?slug=ai-literacy`：学习节点
- `tools.html`：工具目录
- `assistant.html`：站内助手
- `settings.html`：用户空间
- `docs`：接口文档

## 生产环境配置

生产环境至少需要配置：

```powershell
$env:AI_NAV_ENV="production"
$env:AI_NAV_API_WORKERS="1"
$env:AI_NAV_AGENT_RUNTIME_STATE_BACKEND="process_local"
$env:AI_NAV_SECRET_KEY="至少32位的随机密钥"
$env:AI_NAV_CORS_ALLOW_ORIGINS="https://你的站点域名"
$env:AI_NAV_DATABASE_PATH="D:\ai-nav-data\ai_nav.sqlite3"
$env:AI_NAV_UPLOAD_DIR="D:\ai-nav-data\uploads"
$env:AI_NAV_REFRESH_COOKIE_SECURE="1"
$env:RESET_DATABASE_ON_START="0"
```

完整无密钥模板见 `production.env.example`。生产模式会拒绝默认/过短密钥、
非 HTTPS 或通配来源、不安全 Cookie、源码树内数据库/上传目录、全地址空间可信
代理、多 Worker 进程内状态、不安全 Provider/成本/保留期组合，以及任何
`RESET_DATABASE_ON_START=1`。验证脚本设置 `AI_NAV_DISABLE_DOTENV=1`，不会读取真实
`.env`。

## 主要接口

### 公共内容

- `GET /api/v1/navigation`
- `GET /api/v1/learning/roadmap`
- `GET /api/v1/learning/nodes/{slug}`
- `GET /api/v1/learning/search`
- `GET /api/v1/tools/catalog`
- `GET /api/v1/tools/latest`

### 账号与用户空间

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/start`
- `POST /api/v1/auth/password-reset/confirm`
- `GET /api/v1/users/me/account`
- `PATCH /api/v1/users/me/account`
- `GET /api/v1/users/me/profile`
- `PATCH /api/v1/users/me/profile`
- `GET /api/v1/users/me/learning/dashboard`
- `GET /api/v1/users/me/assets/workflows`

### Agent

- `POST /api/v1/agent/chat`
- `GET /api/v1/agent/operations/runtime`（管理员脱敏运行快照）
- `POST /api/v1/agent/workflows/save`

完整接口以运行后的 `/docs` 为准。

## 验证

统一质量门禁（Ruff、依赖审计、发布包排除、全量 Python 测试与分支覆盖率）：

```powershell
.\scripts\verify-quality.ps1
```

全量地基验证：

```powershell
.\scripts\verify-foundation.ps1
```

Agent 专项验证：

```powershell
.\scripts\verify-agent.ps1
```

分区验证：

```powershell
.\scripts\verify-frontend.ps1
.\scripts\verify-learning.ps1
.\scripts\verify-tools.ps1
.\scripts\verify-users.ps1
```

## 项目文档

- `docs/00-index/documentation-map.md`：文档分类、权威顺序和维护规则
- `docs/00-index/http-test-deployment-file-index.md`：HTTP 子路径测试部署的文件、证据和状态入口
- `docs/02-architecture/deployment/http-subpath-test-deployment-design.md`：新旧站共存、测试账号、游客助手与 Provider 预览边界
- `docs/04-operations/deployment/http-test-deployment-runbook.md`：参数化的 HTTP 测试部署、验证、停止与回滚步骤
- `docs/04-operations/deployment/http-test-deployment-troubleshooting.md`：实机部署故障的快速定位、根因、推荐处理和误判边界
- `docs/00-index/remediation-file-index.md`：审计问题到实现、测试、脚本和同步文档的整改索引
- `docs/05-quality/audits/full-project-remediation-verification-report.md`：当前独立复验、实际门禁数字与双重发布结论
- `docs/05-quality/audits/git-commit-readiness-handoff.md`：交给其他 AI 执行暂存、复核和本地提交的安全步骤
- `docs/05-quality/audits/full-project-reaudit-report.md`：当前问题回测、加权复审与生产上线判定
- `docs/05-quality/audits/full-project-remediation-report.md`：七批次整改状态、验证数字与剩余风险
- `docs/05-quality/audits/full-project-audit-report.md`：首轮完整审计基线与原始发现
- `docs/07-prompts/audits/full-project-remediation-prompt.md`：交给新对话执行的全项目整改总控提示词
- `docs/01-overview/fullstack-development-results-handoff.md`：当前全栈成果、生态、架构、模块边界、证据与下一轮审计清单
- `docs/03-domains/agent/agent-development-handoff.md`：当前 Agent 能力、修改边界和渐进开发流程
- `docs/03-domains/users/users-final-acceptance-report.md`：用户空间验收结果
- `docs/04-operations/content/content-operations-runbook.md`：学习与工具内容维护流程
- `docs/04-operations/users/users-release-runbook.md`：用户数据备份、恢复和发布流程

## 后续任务

2026-07-25 独立复验及后续整改确认：全量 176/176 个 Python 测试、34/34 个 Node
测试、36/36 个 JavaScript 语法检查、Ruff 核心规则、依赖审计和 84% 分支覆盖率门槛
均通过。`AUD-API-002` 原有 44 个宽泛输出模型已全部替换为领域字段级响应 DTO，并有
额外内部字段过滤反例；本地整改候选为“通过”。完整结果见
`docs/05-quality/audits/full-project-remediation-verification-report.md`。

当前生产发布仍为 **NO-GO**。上线前必须由对应责任人完成
`docs/04-operations/production-external-signoff-checklist.md`：选择并验证真实恢复发送服务，
签收 Provider 合规与数据政策，配置北京默认业务空间端点及上海服务器出口白名单，执行
受控真实 Provider、C4G 容量、生产备份恢复、回滚、告警和值守演练。未完成这些外部签收时，
不得把本地结果解释为生产验证。当前也不提前加入多 Agent、自动长期记忆、向量库或复杂状态图。
