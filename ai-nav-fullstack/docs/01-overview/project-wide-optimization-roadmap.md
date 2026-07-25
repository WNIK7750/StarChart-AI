# AI 知识导航整体优化任务总纲

## 1. 总目标

把当前“页面可运行、功能骨架已具备”的项目推进为边界清楚、服务可复用、用户体验完整、Agent 可插拔的全栈系统。

总体原则：

- **模块化单体**：一个应用和部署单元；按业务所有权分模块，不把模块模拟成微服务。
- **服务先行**：学习区和工具区提供稳定事实与规则服务。
- **用户层持有体验状态**：进度、最近阅读、收藏、继续学习、偏好和用户资产都归用户层。
- **Agent 只做编排**：Agent 调用领域服务和用户服务，不拥有业务事实，也不绕过服务写数据库。
- **单一事实源**：同一类内容不能长期同时维护在 HTML、JS 和数据库中。
- **渐进替换**：先冻结契约和回归基线，再拆服务、迁数据、改页面。
- **真实数据**：不补假进度、不编造资料、不生成未经校验的站内链接。

当前阶段说明（2026-07-25）：非 Agent 模块和 Agent 离线开发均已完成落地与验收。上线任务统一维护在 `docs/03-domains/agent/agent-development-tasks.md` 与 `docs/03-domains/agent/agent-development-handoff.md`，本早期总路线不再产生新的待办。

## 2. 优化前全项目审计基线

### 2.1 启动时规模

- 后端：FastAPI + SQLite，包含认证、用户、学习、工具和 Agent 路由。
- 前端：5 个原生 HTML 页面和多组 ES modules/内联脚本。
- 学习数据：16 个节点、16 份主资料、64 个目录项、88 条补充链接。
- 工具数据：前端事实源 136 个工具，数据库仅 25 个工具，数据尚未统一。
- 用户数据：账号、资料、偏好、会话、RBAC、登录与审计表已存在；学习状态表尚未落地。
- 测试：Python 和 JavaScript 语法检查通过，工具数据审计通过，但没有正式自动化测试套件。

### 2.2 启动时主要结构问题

| 领域 | 当前问题 | 影响 |
| --- | --- | --- |
| 后端分层 | learning/auth/users 路由直接写 SQL 和业务规则 | 难以单测、复用和替换数据库 |
| 数据迁移 | 启动时执行 schema 和临时 `ALTER TABLE` | 演进不可追踪，生产升级风险高 |
| 工具事实源 | 前端 136 条，数据库 25 条 | 页面、API、搜索和 Agent 结果不一致 |
| 前端架构 | 大型 HTML 内联样式/脚本，`v2-api.js` 职责过多，存在旧脚本双轨 | 修改容易互相覆盖，难做局部测试 |
| 用户体验 | 学习进度、最近阅读、收藏、工作流仍返回 reserved 空数据 | 用户无法形成持续使用闭环 |
| Agent | 仅确定性占位响应，学习工具只有链接生成 | 尚不能基于学习事实服务用户 |
| 导航完整性 | 页面引用 `assistant.html`、`about.html`，文件不存在 | 用户点击后进入 404 |
| 认证客户端 | Access/Refresh Token 存 `localStorage`，401 不自动刷新 | 安全性和会话连续性不足 |
| 运行配置 | 默认开发密钥、宽泛 CORS、应用导入即初始化数据库 | 不适合部署，测试隔离困难 |
| 测试观测 | 无 tests 目录、契约测试、E2E、统一日志和请求 ID | 回归与故障定位成本高 |

## 3. 目标模块和所有权

```text
Frontend Pages
  -> API Client / View Models
     -> HTTP Routers
        -> Module Services
           -> SQLite Repositories

Agent Orchestrator
  -> Learning read facade
  -> Tool catalog facade
  -> User context read facade
  -> User command facade (confirmation required)
```

该结构按需加深，不要求每项功能都创建 schemas、policy、port、adapter 和 facade。跨模块才使用
稳定公开接口；模块内部优先直接调用。详细标准见 `docs/02-architecture/modular-monolith-guidelines.md`。

### 3.1 所有权矩阵

| 数据或能力 | 所有者 | 可消费方 |
| --- | --- | --- |
| 节点、路线、资料、章节、先修关系 | Learning | Web、Users、Search、Agent |
| 工具事实、分类、能力、访问性、链接 | Tools | Web、Search、Agent |
| 账号、资料、偏好、会话、权限 | Users/Auth | Web、Agent 只读上下文 |
| 学习进度、最近阅读、收藏、继续学习 | Users/Learning State | Web、Agent |
| 用户保存的工作流 | Users/Assets | Web、Agent |
| 对话、提示词、模型调用、工具编排 | Agent | Agent 页面 |
| 导航、错误格式、请求上下文 | Platform | 所有模块 |

硬边界：

- Learning 和 Tools 不依赖 Users 或 Agent。
- Users 可引用 Learning/Tools 的稳定业务键并调用其只读 facade。
- Agent 不直接访问业务表，只调用公开 facade。
- 页面不从 DOM、静态数组或 Agent 回复中反推业务事实。

## 4. 用户层学习体验规划

### 4.1 用户层功能组

按业务内聚性管理：

```text
backend/app/users/
  identity/         # 账号、认证、安全、会话、授权
  settings/         # 资料、头像、偏好
  learning_state/   # 进度、活动、继续学习、收藏
  assets/           # 保存的工作流和用户资产
  governance/       # 隐私、审计和命令安全
```

这是所有权模型，不要求把当前已验收目录立即搬迁。后续修改相关功能时，可把只有一个实现且
仅做转发的 port/facade 渐进合并；不得为了目录一致性发起大规模重构。

### 4.2 核心用户体验

#### 学习进度

- 用户主动开始资料时创建 `in_progress` 记录。
- 进度更新必须幂等，支持百分比、完成章节和节点完成。
- `completed` 时记录完成时间；回退进度需要显式行为。
- 节点页展示状态和进度，学习地图显示已开始/已完成状态。
- 进度是用户状态，不写回路线节点或学习内容表。

#### 最近阅读

- 用户打开节点、主资料或补充资料时记录 append-only 活动。
- “最近阅读”按目标去重，保留最后访问时间和最近动作。
- 首页与学习页默认显示最近 3 至 5 项；设置页提供分页历史。
- 只有真实访问触发记录，页面预加载和搜索索引不得产生阅读事件。

#### 继续学习

用户层按以下优先级选择：

1. 最近有 `in_progress` 且未完成的节点。
2. 最近打开但尚未创建进度的节点。
3. 最近完成节点的 `recommended_next`。
4. 无历史时根据 `learningLevel/targetDirection` 返回学习服务的公开推荐。

返回结果由用户状态与学习事实聚合而成，包含 `reasonCode`，例如 `RESUME_IN_PROGRESS`、`CONTINUE_RECENT`、`START_RECOMMENDED`。

#### 收藏

- 统一支持学习节点、资料、链接、工具和工作流。
- 用户表只保存稳定 target key 与必要展示快照。
- 返回收藏列表时按目标类型调用对应领域 facade 补齐当前事实。
- 目标下线时展示“已下线”而不是静默丢失。

### 4.3 用户层表

- `user_learning_progress`
- `user_learning_activity`
- `user_favorites`
- 后续：`user_saved_workflows`、`user_learning_plans`

`user_learning_activity` 建议使用稳定 `target_type + target_key`，并保留可选 `node_slug` 便于聚合。所有私有查询必须以服务端解析的 `user_id` 过滤。

### 4.4 用户 API

```text
GET    /api/v1/users/me/learning/dashboard
GET    /api/v1/users/me/learning/progress
PUT    /api/v1/users/me/learning/progress/{nodeSlug}
POST   /api/v1/users/me/learning/activity
GET    /api/v1/users/me/learning/recent
GET    /api/v1/users/me/learning/resume
GET    /api/v1/users/me/favorites
POST   /api/v1/users/me/favorites
DELETE /api/v1/users/me/favorites/{favoriteUid}
```

写请求要求 `Idempotency-Key` 或业务幂等键；列表接口必须分页；错误返回稳定 code。

### 4.5 页面落点

| 页面 | 用户体验 |
| --- | --- |
| 首页 | 一个清晰的“继续学习”入口和最近阅读摘要 |
| 学习总览 | 路线节点状态、整体进度、最近阅读、收藏筛选 |
| 节点详情 | 开始/继续/完成、目录进度、收藏、最近访问记录 |
| 设置页 | 完整学习历史、收藏管理、进度重置和数据导出入口 |
| Agent 页 | 读取用户偏好和进度；任何写操作先确认 |

视觉方向：安静、紧凑、可扫描。状态使用熟悉图标和清晰标签；不使用大面积营销 Hero、嵌套卡片或只为装饰的动画。

## 5. 分领域优化任务

### 5.1 Platform 与工程地基（P0）

- [x] 建立 `tests/`、测试配置、临时数据库 fixture 和最小 CI 命令。
- [x] 增加统一配置对象，区分 development/test/production。
- [x] 生产环境拒绝默认 `SECRET_KEY`，收紧 CORS origins。
- [x] 将数据库初始化移到 FastAPI lifespan，测试可注入数据库路径。
- [x] 引入版本化迁移目录，停止在启动函数中追加临时 DDL。
- [x] 定义统一错误响应、request ID 和结构化日志。
- [x] 增加 `/health/live` 与 `/health/ready`。

验收：应用可以使用临时数据库启动；迁移可重复执行；生产配置错误时快速失败。

### 5.2 Learning 服务（P0）

- [x] 按 `learning-area-foundation-plan.md` 抽取 schemas、policies、ports、service、SQLite repository。
- [x] 路由只处理 HTTP 映射，不写 SQL。
- [x] 增加路线、节点、搜索、先修、推荐和 Agent context 契约。
- [x] 将 SVG 路径边扩充为语义关系，布局字段仍作为展示元数据。
- [x] 增加内容状态、链接验证时间和稳定资料 UID。

验收：Learning 在没有 Users 和 Agent 时可独立测试和运行。

### 5.3 Users 与 Auth（P0/P1）

- [x] 从 `users.py` 抽出 account/profile/preferences/sessions/learning_state 服务。
- [x] 落地学习进度、活动和收藏迁移。
- [x] 实现 dashboard/recent/resume/progress/favorites API。
- [x] 所有 Users 写操作按风险登记审计、重放防护和并发控制，并由路由覆盖脚本强制校验。
- [x] 实现访问令牌自动刷新与并发刷新锁。
- [x] 评估将 refresh token 迁到 Secure HttpOnly SameSite Cookie；至少不再让长期令牌由任意页面脚本读取。
- [x] 登录、注册、重置密码和用户名探测增加限流。
- [x] 账号枚举、代理头信任和会话撤销行为增加安全测试。

验收：用户可跨会话继续学习；私有数据严格隔离；过期 access token 不会无提示丢失操作。

### 5.4 Tools 服务（P1）

- [x] 以单个内聚 Tools 模块实现，不预拆 catalog/category/collection/link 微服务或同构分层。
- [x] 确认后端数据库为最终唯一事实源。
- [x] 将 136 个前端工具和 138 条 placements 完整迁入数据库。
- [x] 分离工具事实、分类关系、最新运营位、别名和官方链接；能力继续使用标签，暂不预建空的 capability 子服务。
- [x] 保持 catalog/search/collections/agent-context 公开能力稳定。
- [x] 前端改读 API；本地数据只作迁移生成输入，不作第二运行事实源。
- [x] 保留并扩展 `audit-tool-data.mjs` 为迁移前后对账工具。

验收：页面、搜索和 Agent 对同一查询使用同一工具事实，数量和关键字段一致。

持续演进约束：Tools 保持单个内聚模块；目录更新使用追加迁移，运行时对账比较关键字段而不只比较数量。Agent 可以复用 Tools 只读检索，但对话、解释和用户写入不进入 Tools。

### 5.5 Agent（P1/P2）

当前执行任务和阶段门禁已迁移到 `docs/03-domains/agent/agent-development-handoff.md`；以下清单保留为项目级能力摘要。

- [x] 先补齐 `assistant.html` 的真实产品入口，或在完成前移除无效导航。
- [x] 定义稳定输入、输出、引用、工具调用和错误 schema。
- [x] 实现 Learning/Tools/User Context 薄工具适配器。
- [x] 第一阶段只开放读取；用户状态写入需确认和审计。
- [x] 让确定性检索和规则计划在无 LLM 时仍可工作。
- [x] 已接入模型 provider port、可关闭流式响应、短期会话和版本化评估；真实 Provider 默认关闭。
- [x] 已建立 QA、导航、推荐、学习计划、工作流、安全和越权评估集，并纳入离线 Agent 门禁。

验收：替换模型或 Agent 框架不影响 Learning、Tools、Users 的实现与数据。

### 5.6 Frontend（P1）

- [x] 明确 5 个非 Agent 页面和 Agent 页的唯一入口脚本，并由前端入口契约持续检查。
- [x] 从 HTML 中移出业务数据和主要运行逻辑。
- [x] 拆分 `v2-api.js` 为 platform、learning、tools、user 模块。
- [x] 清理 `home.js/learn.js/node.js/roadmap.js/tools.js/layout.js` 双轨代码。
- [x] 建立统一 API client：超时、取消、401 刷新、错误码、重试边界。
- [x] 建立可复用的 loading/empty/error/offline 状态；toast/dialog 经复核没有跨页重复需求，保留领域所有权。
- [x] 修复 `assistant.html/about.html` 缺页链接。
- [x] 对所有服务端文本做安全渲染，对外链限制协议并加 `noopener noreferrer`。
- [x] 覆盖键盘、焦点、reduced motion、360/768/1440 视口。

验收：每个 DOM 容器只有一个渲染所有者；用户操作失败有可恢复反馈；移动端无溢出或遮挡。

### 5.7 数据与内容治理（P2）

- [x] 定义内容 draft/published/archived 生命周期。
- [x] 为学习资料和工具链接增加校验任务、最后验证时间和失效状态。
- [x] 建立 seed、迁移、内容导入和备份恢复流程。
- [x] 增加内容运营边界与发布审计，区分公共业务事实、用户私有状态和 Agent 会话数据。
- [x] 为 SQLite 设置 WAL、busy timeout、完整性校验、在线备份和原子恢复策略；达到并发阈值后再迁 PostgreSQL。

### 5.8 测试、性能与可观测性（贯穿）

- [x] Policy 单元测试。
- [x] Repository 集成测试。
- [x] API 契约与权限测试。
- [x] Agent 工具与引用真实性测试。
- [x] Playwright 关键流程与视觉回归。
- [x] 记录最小化的 operation、latencyMs、resultCount/errorCode 和脱敏 requestId。
- [x] 建立查询基线、慢查询检查和前端性能/响应式门禁。

## 6. 跨模块实施波次

### Wave 0：冻结现状（P0）

1. 创建测试地基和临时数据库。
2. 保存现有 API 契约样例与页面截图。
3. 建立页面入口、无效链接和双轨脚本清单。
4. 固化工具数据审计基线：136 tools / 138 placements。

### Wave 1：后端服务化（P0）

1. 建立配置、lifespan、迁移和错误格式。
2. 抽取 Learning service，保持现有 API 与页面不变。
3. 抽取 Users learning_state，落地真实用户状态表。
4. 实现用户 dashboard/recent/resume/progress/favorites。

### Wave 2：用户体验闭环（P1）

1. API client 自动刷新与错误体验。
2. 节点页记录真实活动并更新进度。
3. 学习页展示节点状态、最近阅读和继续学习。
4. 首页展示继续学习入口。
5. 设置页升级为完整历史与收藏管理。

### Wave 3：工具统一与前端收敛（P1）

1. 工具数据迁库并对账。
2. 页面、搜索、Agent 统一读取 Tools service。
3. 拆分 `v2-api.js`，清理旧脚本和 HTML 业务副本。
4. 补齐 Agent/About 页面或删除未实现导航。

### Wave 4：Agent 可用化（P1/P2）

1. 接入 Learning、Tools、User Context 只读工具。
2. 实现结构化引用、链接守卫和规则型学习计划。
3. 接入模型、流式响应与会话。
4. 开放经用户确认的收藏、进度或工作流保存命令。

### Wave 5：治理与发布（P2）

1. 内容生命周期和链接巡检。
2. 安全限流、Cookie 策略、备份与恢复演练。
3. 完整 E2E、视觉回归、性能预算和可观测性。
4. Feature flags、灰度和回滚方案。

## 7. 首批可执行任务

下一次编码建议落地 **Wave 0 + Wave 1 的最小纵切**：

1. 建立 pytest/TestClient 与临时 SQLite fixture。
2. 增加第一版迁移，创建 `user_learning_progress`、`user_learning_activity`、`user_favorites`。
3. 抽取 Learning 只读 service，保持三个现有接口兼容。
4. 创建 Users `learning_state` service。
5. 实现 `POST activity`、`PUT progress`、`GET recent`、`GET resume`。
6. 先在节点页接入 `view_node` 和开始学习，首页/学习页接入继续学习。
7. 加入用户隔离、幂等、匿名行为和 API 契约测试。

这个纵切能尽早交付真实用户价值，同时验证 Learning 与 Users 的低耦合边界；无需等待 Agent 或工具数据迁移完成。

## 8. 项目级完成定义

- 每类事实只有一个运行时主数据源。
- API、Agent 和前端都通过服务契约访问业务能力。
- 用户状态归 Users，学习事实归 Learning，工具事实归 Tools。
- Agent 可替换、可关闭，且不影响普通学习和工具体验。
- 所有用户私有写操作可鉴权、可审计、可幂等、可恢复。
- 关键业务拥有单元、集成、契约和浏览器测试。
- 页面无无效导航、双重渲染、虚假状态和不可恢复错误。
- 生产配置、迁移、备份、日志和健康检查可独立验证。
