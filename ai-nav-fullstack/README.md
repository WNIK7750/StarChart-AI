# AI 知识导航前后端分离版

这是 `design/v2` 四个页面的前后端分离实现。前端负责页面结构、样式、动画和交互；导航、知识地图、学习资源、节点介绍、工具分类、工具列表、用户账号和 Agent 占位能力均通过后端 API 获取。

当前学习区已经支持：

- 节点主资料、章节目录、建议学习时长和概览。
- 主资料合入资料列表，并显示“主资料”标签。
- 资料访问标签：“国内可访问”和“外网”。
- 每个学习模块包含多条国内可访问资源和视频资料。

当前用户区已经支持：

- 注册、登录、刷新 Token、退出登录。
- 当前用户资料和偏好读取、修改。
- 登录会话查询。
- 学习进度、收藏、用户工作流接口位。暂无真实数据时只返回空集合和 `reserved` 元信息，不写入虚假数据。

当前 Agent 区已经支持：

- `POST /api/v1/agent/chat` 结构化接口入口。
- `backend/app/agent/` 模块化骨架，包含 schema、router、service、tools、memory、evaluator。
- 当前阶段只返回占位响应，后续可逐步接入检索、工具调用、链接校验、工作流生成和会话存储。

## 目录结构

```text
ai-nav-fullstack/
  backend/             FastAPI 后端服务
    app/api/v1/routers 后端 API 路由
    app/agent          Agent 模块化骨架
    app/core           配置与安全能力
    app/db             数据库连接与初始化
  database/            SQLite schema、seed 和学习内容数据
  frontend/            静态前端页面与 JS/CSS 模块
  docs/                数据库、用户模块、Agent 和 Git 文档
```

## 启动

```powershell
cd D:\Web期末作业\ai-nav2\ai-nav-fullstack
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\run.py
```

打开：

- 首页：`http://127.0.0.1:8088/index.html`
- 学习页：`http://127.0.0.1:8088/learn.html`
- 节点页：`http://127.0.0.1:8088/learn-node.html?slug=ai-literacy`
- 工具页：`http://127.0.0.1:8088/tools.html`
- 用户设置页：`http://127.0.0.1:8088/settings.html`
- API 文档：`http://127.0.0.1:8088/docs`

## API

- `GET /api/v1/navigation`
- `GET /api/v1/learning/roadmap`
- `GET /api/v1/learning/resources?domain=core`
- `GET /api/v1/learning/nodes/{slug}`
- `GET /api/v1/tools/categories`
- `GET /api/v1/tools`
- `GET /api/v1/tools/latest`
- `GET /api/v1/tools/workflows`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/username-available`
- `POST /api/v1/auth/password-reset/security/start`
- `POST /api/v1/auth/password-reset/security/verify`
- `POST /api/v1/auth/password-reset/security/confirm`
- `GET /api/v1/users/me/account`
- `PATCH /api/v1/users/me/account`
- `PATCH /api/v1/users/me/password`
- `GET /api/v1/users/me/security-questions`
- `PUT /api/v1/users/me/security-questions`
- `GET /api/v1/users/me/profile`
- `PATCH /api/v1/users/me/profile`
- `POST /api/v1/users/me/avatar`
- `GET /api/v1/users/me/preferences`
- `PATCH /api/v1/users/me/preferences`
- `GET /api/v1/users/me/sessions`
- `GET /api/v1/users/me/learning/progress`
- `GET /api/v1/users/me/favorites`
- `GET /api/v1/users/me/workflows`
- `POST /api/v1/agent/chat`

## 数据维护

学习区内容集中维护在 `database/learning_content.sql`：

- `learning_materials`：每个节点的主资料。
- `learning_material_sections`：主资料目录和建议学习时长。
- `learning_node_tags`：节点标签。
- `learning_node_links`：补充资料、视频、文档和课程链接。

资料访问类型使用 `access_type` 标记：

- `cn`：国内可访问。
- `external`：外网资源。

用户模块 Phase 1 已落地到 `database/schema.sql`，包含用户账号、密码认证、会话、资料、偏好、角色权限、登录日志和审计日志。默认启动不会删除已有数据库；如需开发期重建数据库，可设置环境变量 `RESET_DATABASE_ON_START=1` 后启动。

## 前端数据调用约定

- 所有页面数据通过 `frontend/assets/js/api.js` 调用后端接口。
- 登录态由前端 API 层统一附加 Bearer Token。
- 没有真实数据的用户私有列表只渲染后端返回的空集合和说明，不在前端制造假数据。
- 后续 Agent 前端接入时，应直接调用 `/api/v1/agent/*`，不要在页面内写死 Agent 输出。
