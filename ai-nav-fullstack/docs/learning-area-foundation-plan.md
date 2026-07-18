# 学习区地基化优化规划

## 1. 规划定位

本轮不是单纯重做学习页，而是把学习区建设为一个可独立演进、可被多端复用的“学习能力服务”。网页、站内搜索、用户学习空间和未来 Agent 都只能通过稳定契约使用学习能力，不直接依赖彼此的页面结构、SQL、内部函数或编排框架。

核心目标：

- 学习区自身低耦合：展示、应用逻辑、领域规则、数据访问分层。
- 学习区与 Agent 低耦合：Agent 只依赖公开的学习能力端口和结构化 DTO。
- 服务优先：先形成可复用的查询、检索、规划、进度与推荐能力，再扩展 UI 和 Agent 编排。
- 渐进迁移：保持现有 URL 和主要 API 可用，按阶段替换内部实现。
- 可验证：每项能力都有契约测试、业务测试或端到端验收条件。

### 1.1 当前实现状态

截至 2026-07-12，本任务已完成学习区服务地基与用户体验收口：

- Learning repository/service 已抽取，原有三个接口保持兼容。
- 学习搜索、Agent context 和下一节点只读接口已提供。
- Users `learning_state` 已实现真实进度、活动、最近阅读、继续学习和收藏。
- 首页、学习页、节点页和设置页已接入用户状态。
- 用户状态迁移、4 项分层测试和桌面/移动浏览器回归已通过。
- 企业级加固已完成严格 DTO、迁移 checksum、原子并发控制、审计、幂等、分页和前端冲突恢复。
- 稳定章节 UID、章节级完成状态、节点进度原子聚合和语义关系服务已落地。
- 契约快照、独立 Learning CI、12 项后端测试与 2 项前端测试已建立，桌面/移动章节交互回归通过。
- 内容治理迁移、匿名阅读幂等导入、最近阅读分页/本地时间、可重试错误态和前端 API 适配层已完成。
- 内容完整性门禁、服务性能基线、访问观测和公开读取缓存策略已进入验证脚本。

详细文件和验证结果见 `docs/learning-area-implementation.md`。学习核心后续只接受契约内迭代；内容运营界面、Agent 计划编排和平台级基础设施由各自分区继续实现。

## 2. 当前基线与主要问题

### 2.1 已有基础

- `database/schema.sql` 已包含知识领域、难度、路线节点、关系、资料、目录、标签和资源表。
- `backend/app/api/v1/routers/learning.py` 已提供路线图、推荐资源和节点详情接口。
- `frontend/learn.html`、`frontend/learn-node.html` 已有完整视觉页面，并由 `frontend/assets/js/v2-api.js` 注入后端数据。
- 用户区已预留学习进度接口，Agent 已有独立模块骨架。
- 工具区已经采用“领域服务被 API 与 Agent 共同复用”的雏形，可作为学习区改造的参考。

### 2.2 需要解决的耦合

1. **路由与数据库耦合**：学习路由直接写 SQL、聚合统计、拼装返回值和生成文案，HTTP 层承担了过多职责。
2. **业务规则无独立归属**：主资料选择、学习时长汇总、前后节点计算和领域筛选规则都藏在路由函数中。
3. **Agent 学习能力为空壳**：`backend/app/agent/tools/learning_tools.py` 目前只生成节点链接，无法检索节点、读取上下文或生成学习计划。
4. **前端存在双轨实现**：`learn.js/roadmap.js/node.js` 与 `v2-api.js` 同时保留；旧 `node.js` 还读取已经不存在的 `data.lessons` 字段。
5. **前端模块职责过大**：`v2-api.js` 同时处理导航、认证、搜索、工具区和学习区，学习能力难以独立测试与复用。
6. **页面保留静态业务副本**：学习路线和资源存在静态兜底内容与内联交互，容易与后端真实数据漂移。
7. **缺少显式契约**：接口主要返回自由字典，没有 Pydantic 响应模型、版本语义、错误码和契约测试。
8. **学习状态尚未落地**：进度、活动、收藏和最近学习目前只是预留响应，无法支持个性化服务。
9. **缺少服务级测试与观测**：未发现学习领域测试；无法稳定衡量查询质量、进度写入和 Agent 调用结果。

## 3. 目标架构

```text
Web Page / Search / Agent / Future Clients
                 |
          Adapter Layer
  HTTP Router / Agent Tool / Frontend API
                 |
       Learning Application Service
  query roadmap | get node | search | plan rules
  prerequisites | recommend content | references
                 |
          Domain Policies
 prerequisite | duration | completion | ranking
                 |
       Repository Interfaces (Ports)
                 |
      SQLite Repositories (Adapters)
```

### 3.1 依赖规则

- `api` 可以依赖 `learning.application`，不能直接访问学习表。
- `agent.tools` 可以依赖 `learning.application` 或只读 facade，不能导入学习路由或前端代码。
- `learning.application` 依赖 repository protocol，不依赖 FastAPI、Agent 框架或浏览器。
- SQLite repository 实现 protocol，SQL 只出现在 repository 层。
- 前端学习模块只依赖 `learning-api.js` 返回的稳定 ViewModel，不拼装服务端业务规则。
- 学习核心服务不接收或持有 `user_id`；用户层通过稳定的 `node_slug`、资料 UID 和章节 UID 关联学习事实。
- 最近阅读、进度、收藏、继续学习和个性化聚合归用户层所有；用户层可调用学习服务补齐标题、链接、时长和节点关系。
- Agent 的模型、提示词、会话记忆和工具编排不得进入学习领域服务。

### 3.2 推荐目录

```text
backend/app/
  learning/
    __init__.py
    schemas.py          # 领域 DTO、查询条件、结果类型
    policies.py         # 完成度、时长、先修与排序规则
    ports.py            # repository protocol
    service.py          # 用例编排和统一 facade
    repositories/
      sqlite.py         # SQLite 查询与持久化
  api/v1/routers/
    learning.py         # HTTP 参数和响应映射
  users/
    learning_state/     # 用户进度、阅读活动、收藏与继续学习
  agent/tools/
    learning_tools.py   # Agent 薄适配器

frontend/assets/js/
  learning/
    learning-api.js
    learning-store.js
    roadmap-view.js
    node-view.js
    progress-view.js
    learning-page.js
```

首轮无需引入 DI 框架。使用构造函数参数或模块级工厂注入 repository，保持简单且可测试。

## 4. 学习服务能力边界

### 4.1 只读核心能力

| 能力 | 服务方法 | 主要消费者 |
| --- | --- | --- |
| 获取路线图 | `get_roadmap(filters)` | Web、搜索、Agent |
| 获取节点详情 | `get_node(slug)` | Web、用户层、Agent |
| 搜索学习内容 | `search_learning(query, filters, limit)` | 搜索、Agent |
| 获取 Agent 上下文 | `get_agent_context(query, limit)` | Agent |
| 获取先修与内容下一步 | `recommend_next(node_slug)` | Web、用户层、Agent |
| 生成规则型计划骨架 | `build_plan_skeleton(goal, constraints)` | 用户层、Agent、Web |

`get_agent_context` 必须返回紧凑、可引用、可校验的数据，而不是完整页面 DTO。建议字段：

```json
{
  "query": "学习 RAG",
  "nodes": [
    {
      "slug": "rag",
      "title": "RAG",
      "summary": "...",
      "difficulty": "advanced",
      "prerequisiteSlugs": ["embedding", "llm-basics"],
      "estimatedMinutes": 180,
      "href": "learn-node.html?slug=rag",
      "evidence": [{"sourceType": "material", "sourceId": "..."}]
    }
  ]
}
```

### 4.2 用户状态能力归属

以下能力不属于学习服务，必须在用户层的 `learning_state` 子域实现：

- `get_learning_dashboard(user_id)`：进度摘要、最近阅读、继续学习和收藏概览。
- `record_learning_activity(user_id, command)`：查看节点、开始资料、打开资源、完成章节。
- `set_node_progress(user_id, command)`：幂等更新用户节点进度。
- `add_favorite/remove_favorite(user_id, target)`：管理用户收藏。
- `get_resume_target(user_id)`：基于用户活动与进度选择继续学习目标。

用户层持有身份、权限、时间线和个性化状态，并通过学习服务读取节点、资料、章节、先修和链接事实。学习服务不得反向依赖用户层。Agent 读取用户状态时调用用户层只读 facade；Agent 写入用户状态时必须经过用户层命令接口、显式用户确认、幂等键和审计。

### 4.3 明确排除项

学习服务不负责：

- LLM 调用、提示词和模型选择。
- Agent 会话、长期记忆和工具调度。
- HTML、CSS、DOM 或页面动画。
- 认证令牌解析。
- 用户进度、最近阅读、收藏、笔记和学习活动持久化。
- 第三方网页抓取。
- 将模型生成内容直接写入正式学习内容库。

## 5. 稳定契约设计

### 5.1 DTO 原则

- 对外字段统一 camelCase，Python 内部可使用 snake_case 并通过 alias 输出。
- 响应 DTO 不暴露数据库自增 ID；使用 `slug`、稳定内容 UID 或引用对象。
- URL 由统一链接生成器构建，Agent 不自由拼接站内链接。
- 时间同时返回数值字段 `estimatedMinutes`，展示文案由客户端本地化；旧 `suggestedDuration` 暂时兼容。
- 所有列表定义稳定排序规则，并返回可选 `meta.contractVersion`。
- 错误使用稳定 code，例如 `LEARNING_NODE_NOT_FOUND`、`INVALID_DOMAIN`、`PROGRESS_CONFLICT`。

### 5.2 API 演进

保留现有接口：

- `GET /api/v1/learning/roadmap`
- `GET /api/v1/learning/resources`
- `GET /api/v1/learning/nodes/{slug}`

新增服务型接口：

- `GET /api/v1/learning/search?q=&domain=&difficulty=&limit=`
- `GET /api/v1/learning/agent-context?q=&limit=`
- `GET /api/v1/learning/nodes/{slug}/next`
- `POST /api/v1/learning/plans/preview`
- `GET /api/v1/users/me/learning/state`
- `PUT /api/v1/users/me/learning/progress/{nodeSlug}`
- `POST /api/v1/users/me/learning/activity`

旧接口内部改为调用新 service，不做一次性破坏式改名。只有在契约测试覆盖后，才清理兼容字段。

## 6. 数据地基任务

### 6.1 现有模型校正

- 为路线节点补充可检索摘要、学习目标和预计总时长的明确来源。
- 将边从纯 SVG `path_d` 扩展为语义关系：`source_slug`、`target_slug`、`relation_type`；`path_d` 仅作为当前 Web 布局元数据。
- 区分 `prerequisite`、`recommended_next`、`related`，供学习计划和 Agent 推理使用。
- 为资料增加稳定 UID、质量状态、最后验证时间和来源可信等级。
- 内容状态使用 draft/published/archived 或等价字段，避免仅靠 `is_active` 表达全部生命周期。

### 6.2 用户层学习状态表

这些表位于同一数据库的用户层所有权边界内，由用户层 repository 管理；学习服务只提供被引用对象的存在性与展示事实。建议优先新增：

- `user_learning_progress`：节点状态、完成度、最后学习时间、版本号。
- `user_learning_activities`：append-only 学习事件，用于审计和恢复。
- `user_favorites`：统一收藏节点、资料、工具和工作流。

约束：

- `UNIQUE(user_id, node_slug)` 保证进度幂等。
- 更新携带 `version` 或 `updated_at`，避免多端覆盖。
- 完成度限制为 0 到 100；状态限定 `not_started/in_progress/completed`。
- 删除内容时保留历史引用可解释性，优先软下线。

数据库变更应通过独立迁移脚本执行；不要继续把长期演进全部塞进启动时 `ALTER TABLE`。

## 7. 前端优化方向

设计方向：面向持续学习的安静、清晰、可扫描工作台。知识图谱保留为识别性元素，但应服务于“我在哪里、下一步是什么、如何继续”，不只作为动态展示。

### 7.1 信息架构

- 学习总览：继续学习、路径切换、节点状态、推荐资料。
- 节点详情：目标、先修、主资料、目录、实践任务、相关资料、下一步。
- 登录后状态：最近学习、进度、收藏；未登录时明确保持只读。
- Agent 入口只作为上下文动作，例如“解释本节点”“生成本节点学习计划”，不侵入核心阅读流程；进度和最近阅读仍由用户层记录。

### 7.2 工程拆分

- 将学习 API 调用集中到 `learning-api.js`。
- 将 DTO 到页面 ViewModel 的转换集中到 mapper/store。
- 让 roadmap、resource list、node detail、progress 成为独立渲染模块。
- 每个页面入口只负责组合模块、加载状态和错误边界。
- 移除内联重复领域映射，领域与节点关系只以服务响应为准。
- 完成迁移后删除未被 HTML 引用的旧学习脚本，避免双轨维护。
- 所有服务端文本进入 DOM 前统一转义；外链增加允许协议检查和 `rel="noopener noreferrer"`。

## 8. Agent 适配原则

Agent 学习工具保持薄层：参数校验 -> 调用学习 service -> 转换为工具 schema。禁止在工具中复制 SQL、搜索排序和学习计划规则。

第一批工具：

- `search_learning_nodes(query, filters, limit)`
- `get_learning_node_context(slug)`
- `recommend_learning_next(slug, user_id=None)`
- `preview_learning_plan(goal, constraints, user_id=None)`

后续写工具：

- `record_learning_progress(...)`
- `save_learning_plan(...)`

写工具需要：已认证身份、用户显式确认、幂等键、审计记录。Agent 不得绕过 service 直接写表。

## 9. 分阶段任务清单

### Phase 0：契约冻结与回归基线（P0）

- [ ] 保存现有三个学习接口的真实响应样例。
- [ ] 为路线图、资源和节点详情建立 Pydantic 响应模型。
- [ ] 增加 API 契约测试和节点 404 测试。
- [ ] 列出 `learn.html`、`learn-node.html` 实际加载脚本，标记旧双轨代码。
- [ ] 建立桌面与移动端截图基线。

验收：重构前已有行为可自动比较；接口字段、排序和错误行为有明确基线。

### Phase 1：抽取学习领域服务（P0）

- [ ] 创建 `backend/app/learning` 包及 DTO、ports、service。
- [ ] 将学习 SQL 迁入 SQLite repository。
- [ ] 将时长、主资料、导航与领域筛选规则迁入 policy/service。
- [ ] 将 learning router 改为薄适配器，并保持旧接口响应兼容。
- [ ] 使用临时 SQLite fixture 对 service 和 repository 分层测试。

验收：learning router 不再包含 SQL；service 测试不需要启动 FastAPI；现有页面无回归。

### Phase 2：搜索与 Agent 只读服务（P0）

- [ ] 建立学习内容搜索文档和标准化关键词策略。
- [ ] 实现 `search_learning` 与 `get_agent_context`。
- [ ] 建立统一站内学习链接生成器和引用结构。
- [ ] 扩展 Agent learning tools，仅调用学习 service。
- [ ] 在 Agent evaluator 中校验节点 slug、引用和站内链接。
- [ ] 建立至少 20 条学习检索/导航评估用例。

验收：Agent 能用站内真实数据返回节点、理由、先修和有效链接；无结果时不编造内容。

### Phase 3：前端模块化与体验地基（P1）

- [ ] 从 `v2-api.js` 抽出学习 API、store 和 view modules。
- [ ] 去除页面内联 `domainNodes` 业务副本和重复事件绑定。
- [ ] 清理或归档未使用的 `learn.js/roadmap.js/node.js` 双轨实现。
- [ ] 实现统一 loading、empty、error、retry 状态。
- [ ] 增加节点先修、下一步和可访问性语义。
- [ ] 完成 360px、768px、1440px 视口视觉与交互回归。

验收：学习页面入口只负责编排；没有从 DOM 反推业务数据；键盘可访问且移动端无溢出。

### Phase 4：用户进度与继续学习（P1）

- [ ] 在用户层增加进度、活动和收藏迁移脚本。
- [ ] 创建用户层 `learning_state` repository、service 和薄路由。
- [ ] 由用户层落地进度写入、最近阅读、继续学习和收藏接口。
- [ ] 用户层聚合学习服务的公开事实，禁止复制学习内容快照作为主数据。
- [ ] 首页、学习页、节点页和设置页消费用户层真实状态，不制造默认进度。
- [ ] 为幂等、越权、并发覆盖和未登录写入增加测试。

验收：用户可跨会话继续学习并查看最近阅读；不同用户数据隔离；重复提交不会产生错误进度；学习服务在无用户模块时仍可独立运行。

### Phase 5：学习计划服务与 Agent 增强（P2）

- [ ] 基于语义边、用户水平和时间约束实现规则型计划预览。
- [ ] 计划结果包含节点、顺序、理由、预计时长和引用。
- [ ] 允许 Agent 在规则结果之上生成自然语言说明，但不得修改事实字段。
- [ ] 用户确认后再保存计划；计划保存不依赖 Agent 会话。
- [ ] 建立计划完整度、先修合法性和时长约束评估。

验收：关闭 LLM 时仍能生成合法的基础计划；更换 Agent 框架不影响学习服务与数据。

### Phase 6：运营、观测与内容治理（P2）

- [ ] 增加学习服务日志：operation、resultCount、latencyMs、errorCode、viewerType。
- [ ] 增加资源链接检查、内容版本和下线流程。
- [ ] 建立服务性能基线与慢查询检查。
- [ ] 为新接口增加限流、缓存策略和缓存失效规则。
- [ ] 建立 feature flag，支持独立关闭 Agent 写操作或新计划能力。

验收：问题可定位、能力可灰度、内容可维护、失败可降级到只读基础路径。

## 10. 推荐执行顺序与依赖

```text
Phase 0
  -> Phase 1
     -> Phase 2 -> Agent 只读接入
     -> Phase 3 -> 前端模块化
     -> Phase 4 -> 真实学习状态
        -> Phase 5 -> 个性化学习计划
           -> Phase 6 -> 规模化治理
```

Phase 2 和 Phase 3 可在 Phase 1 完成后并行。Phase 5 不应早于语义边和真实用户状态，否则只能产出不可验证的表面计划。

## 11. 测试矩阵

| 层级 | 必测内容 |
| --- | --- |
| Policy 单元测试 | 时长、先修、完成度、排序、下一步规则 |
| Repository 集成测试 | SQL 映射、过滤、排序、事务、用户隔离 |
| Service 测试 | 用例组合、无数据、无效 slug、匿名与登录态 |
| API 契约测试 | schema、状态码、字段兼容、错误 code |
| Agent 工具测试 | 参数限制、空结果、链接白名单、引用真实性 |
| 前端 E2E | 路线筛选、节点跳转、标签页、错误重试、继续学习 |
| 视觉回归 | 桌面、平板、移动、长文本、无动画偏好 |

## 12. 完成定义

每个阶段只有同时满足以下条件才算完成：

- 代码依赖符合目标分层，没有新增跨层直连。
- 新旧契约变化有测试和迁移说明。
- 空态、错误态、未登录态和权限失败均有明确行为。
- Agent 所用事实能追溯到学习服务返回的稳定引用。
- 文档、接口模型、实现和测试保持一致。
- 不引入虚假学习进度、虚假资料或模型自由生成的站内链接。

## 13. 首个实施批次

建议下一次编码只做 Phase 0 + Phase 1，控制改动面：

1. 冻结现有 API 契约。
2. 创建学习领域包与 repository protocol。
3. 原样迁移三类查询和现有业务规则。
4. 让原路由调用 service，保持前端零改动。
5. 增加 service、repository、API 三层测试。

这一批完成后，学习区才真正拥有可供 Agent 和前端共同消费的地基；之后再并行做 Agent 检索与前端模块化，风险最低。
