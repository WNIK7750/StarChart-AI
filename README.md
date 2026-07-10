# AI 知识导航

AI 知识导航是一个面向 AI 学习、工具检索和工作流生成的前后端分离项目。当前实现以 `design/v2` 中的页面为视觉参考，覆盖首页、学习路径页、学习节点介绍页和工具页，并通过后端 API 统一提供导航、知识地图、学习资料、节点目录、工具数据和用户账号能力。

## 项目特点

- 前后端分离：前端页面通过 `/api/v1` 接口获取数据，不直接写死业务数据。
- 数据集中维护：学习路线、节点主资料、补充资料、工具分类、用户账号和偏好配置均由后端与 SQL 结构管理。
- 国内学习友好：学习资料区分“国内可访问”和“外网”，便于面向中文用户服务。
- 用户模块已起步：支持注册、登录、刷新 Token、退出、资料维护、偏好维护和登录会话查询。
- 数据接口原子化：暂无真实数据的用户学习进度、收藏、工作流接口返回空集合和 `reserved` 元信息，不写入虚假数据。
- Agent 模块预留：后端已按 Router、Service、Schema、Tools、Evaluator、Memory 拆分，方便后续替换或扩展。

## 目录结构

```text
ai-nav2/
  design/               v2 页面参考稿与设计资产
  ai-nav-fullstack/     当前前后端分离实现
    backend/            FastAPI 后端服务
    database/           SQLite 表结构、基础数据和学习内容数据
    frontend/           静态页面、样式和前端 API 调用逻辑
    docs/               数据库、用户模块、Agent 与 Git 相关文档
  assets/               旧版静态资源
  README.md             项目总说明
```

## 快速启动

```powershell
cd D:\Web期末作业\ai-nav2\ai-nav-fullstack
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\run.py
```

启动后访问：

- 首页：`http://127.0.0.1:8088/index.html`
- 学习路径：`http://127.0.0.1:8088/learn.html`
- 学习节点介绍：`http://127.0.0.1:8088/learn-node.html?slug=ai-literacy`
- 工具页：`http://127.0.0.1:8088/tools.html`
- 用户设置页：`http://127.0.0.1:8088/settings.html`
- API 文档：`http://127.0.0.1:8088/docs`

## 核心接口

- `GET /api/v1/navigation`：顶部导航
- `GET /api/v1/learning/roadmap`：学习路径知识地图
- `GET /api/v1/learning/resources`：学习页推荐资源卡片
- `GET /api/v1/learning/nodes/{slug}`：学习节点介绍、主资料、目录和补充资料
- `GET /api/v1/tools/categories`：工具分类
- `GET /api/v1/tools`：工具列表
- `GET /api/v1/tools/latest`：最新工具
- `GET /api/v1/tools/workflows`：工具工作流
- `POST /api/v1/auth/register`：用户注册
- `POST /api/v1/auth/login`：用户登录
- `POST /api/v1/auth/refresh`：刷新访问令牌
- `POST /api/v1/auth/logout`：退出登录
- `GET /api/v1/auth/me`：当前用户
- `GET /api/v1/auth/username-available`：检查用户名是否可用
- `POST /api/v1/auth/password-reset/security/start`：登录页密保找回密码，发起密保验证
- `POST /api/v1/auth/password-reset/security/verify`：校验密保答案，返回一次性重置令牌
- `POST /api/v1/auth/password-reset/security/confirm`：使用重置令牌设置新密码
- `GET /api/v1/users/me/account`：当前用户账号信息
- `PATCH /api/v1/users/me/account`：修改当前用户用户名
- `PATCH /api/v1/users/me/password`：修改当前用户密码，并使旧访问令牌失效
- `GET /api/v1/users/me/security-questions`：用户设置页读取密保问题状态，不返回答案
- `PUT /api/v1/users/me/security-questions`：用户设置页保存密保问题，需要当前密码确认
- `GET /api/v1/users/me/profile`：当前用户资料
- `PATCH /api/v1/users/me/profile`：修改当前用户资料
- `POST /api/v1/users/me/avatar`：上传并压缩当前用户头像
- `GET /api/v1/users/me/preferences`：当前用户偏好
- `PATCH /api/v1/users/me/preferences`：修改当前用户偏好
- `GET /api/v1/users/me/sessions`：当前用户登录会话
- `GET /api/v1/users/me/learning/progress`：学习进度接口位，暂无真实数据时返回空集合和 `reserved`
- `GET /api/v1/users/me/favorites`：收藏接口位，暂无真实数据时返回空集合和 `reserved`
- `GET /api/v1/users/me/workflows`：用户工作流接口位，暂无真实数据时返回空集合和 `reserved`
- `POST /api/v1/agent/chat`：Agent 模块化聊天入口，当前返回结构化占位响应

## 数据维护

主要数据文件位于：

- `ai-nav-fullstack/database/schema.sql`：数据库表结构
- `ai-nav-fullstack/database/seed.sql`：导航、路线图、工具库基础数据
- `ai-nav-fullstack/database/learning_content.sql`：学习节点主资料、目录、标签和补充资料

新增学习资料时，建议优先维护 `learning_content.sql` 中的 `learning_node_links`。其中：

- `access_type = 'cn'` 表示国内可访问。
- `access_type = 'external'` 表示需要外网访问。
- `link_type = 'video'` 表示视频资料。

用户相关数据不和学习内容混写。账号、认证、资料、偏好、角色、权限、会话、登录日志等表位于 `schema.sql`，后续学习进度、收藏和工作流应继续按用户私有数据表拆分。

## Git 使用建议

```powershell
git status
git add .
git commit -m "完善用户模块与Agent接口预留"
```

提交前建议确认：

- 没有把 `.venv/`、运行时数据库、测试截图等本地文件加入版本库。
- README、数据库说明、用户模块文档和 Agent 文档均为中文说明。
- 后端接口、前端页面、注册登录流程和用户空间占位接口均可正常运行。
