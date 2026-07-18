# AI 知识导航

本目录是 AI 知识导航的当前可运行版本，包含网站页面、业务接口、数据库迁移、自动化测试和 Agent 后续开发资料。

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

- 数据库保存 136 条工具事实，其中 134 条公开、2 条归档。
- 支持分类、子分类、搜索、免费优先、最新工具和工作流推荐。
- 多页分类在桌面端使用固定三列四行目录，卡片尺寸和分页器位置保持稳定。
- 移动端改为单列自然滚动，不保留桌面端空位。
- 链接健康状态、最后检查时间和归档状态可通过维护脚本更新。

### 用户空间

- 支持注册、登录、刷新、退出、设备会话查看和其他设备退出。
- 支持用户名、邮箱和手机号登录，手机号会统一为标准格式保存。
- 账号页可修改用户名、邮箱和手机号；联系方式变更要求当前密码。
- 支持头像裁剪上传、公开资料、学习偏好、密保问题和密码修改。
- 支持协议同意、撤回、数据导出、注销申请及撤销。
- 支持学习概览、最近阅读、收藏和个人工作流资产。

### Agent 地基

- `POST /api/v1/agent/chat` 返回结构化回答、站内引用和工作流草案。
- Agent 可读取学习内容、工具目录以及用户允许使用的最小上下文。
- 工作流保存必须经过用户确认，并使用幂等键防止重复写入。
- 当前保留确定性回答模式，未接入真实模型 Provider、SSE 会话、长期记忆或多 Agent。
- 后续开发顺序见 `docs/agent-delivery-roadmap.md`。

### 安全与运行

- 数据库使用 17 个增量迁移，并记录迁移校验值。
- 登录具备失败锁定、速率限制、刷新令牌轮换和会话撤销。
- 写操作具备权限校验、审计事件、稳定错误码和请求编号。
- 提供数据库备份、恢复、完整性检查、外键检查和发布演练。

## 目录结构

```text
ai-nav-fullstack/
  backend/                FastAPI 应用与业务功能
  database/               初始结构、基础数据和 17 个迁移
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
$env:AI_NAV_SECRET_KEY="至少32位的随机密钥"
$env:AI_NAV_CORS_ALLOW_ORIGINS="https://你的站点域名"
$env:AI_NAV_DATABASE_PATH="D:\ai-nav-data\ai_nav.sqlite3"
$env:AI_NAV_REFRESH_COOKIE_SECURE="1"
```

生产模式会拒绝默认密钥、过短密钥、通配来源和不安全的刷新 Cookie。

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
- `GET /api/v1/users/me/account`
- `PATCH /api/v1/users/me/account`
- `GET /api/v1/users/me/profile`
- `PATCH /api/v1/users/me/profile`
- `GET /api/v1/users/me/learning/dashboard`
- `GET /api/v1/users/me/assets/workflows`

### Agent

- `POST /api/v1/agent/chat`
- `POST /api/v1/agent/workflows/save`

完整接口以运行后的 `/docs` 为准。

## 验证

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

- `docs/pre-agent-foundation-final-report.md`：Agent 开发前的地基验收结果
- `docs/agent-development-handoff.md`：当前 Agent 能力和修改边界
- `docs/agent-delivery-roadmap.md`：从模型接入到发布收口的任务顺序
- `docs/users-final-acceptance-report.md`：用户空间验收结果
- `docs/content-operations-runbook.md`：学习与工具内容维护流程
- `docs/users-release-runbook.md`：用户数据备份、恢复和发布流程

## 后续任务

下一阶段从真实模型只读回答开始，随后依次完成流式会话、经确认的用户写入、质量评估、兼容性验证和发布收口。当前不提前加入多 Agent、长期记忆或复杂状态图。
