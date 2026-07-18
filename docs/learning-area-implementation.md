# 学习区地基与用户体验实现记录

## 已实现范围

### Learning 服务

- 新增 `backend/app/learning/`，包含 policy、repository port、SQLite adapter 和 service facade。
- `learning.py` 路由已变为 HTTP 薄适配器，不再包含学习 SQL。
- 保持原有路线图、资源和节点详情接口兼容。
- 新增学习搜索、Agent 紧凑上下文和下一节点接口。
- 新增稳定章节 UID、路线语义关系与独立关系查询；Agent 上下文只消费结构化关系事实。
- 主资料与补充链接具备稳定 UID、发布状态、内容版本、质量状态、来源可信等级和校验时间。
- 主资料与补充链接具有独立链接健康状态；显式巡检写回，普通启动和 CI 不访问第三方网站。
- Agent 学习工具只调用 Learning service，不读取页面或数据库。

### Users 学习状态

- 新增 `backend/app/users/learning_state/`，状态所有权与 Learning 分离。
- 新增真实进度、append-only 阅读活动和收藏表。
- 新增 dashboard、progress、activity、recent、resume、favorites API。
- 进度支持幂等 upsert、状态推导、版本冲突和用户隔离。
- 章节完成状态由 Users 持有；章节写入、节点进度聚合和审计日志在同一事务提交。
- 匿名浏览仅保存真实节点访问；登录后经校验和幂等导入形成最近阅读，不制造学习进度。
- 最近阅读只由真实页面访问或资料打开产生，不自动制造进度。
- 继续学习依次选择学习中节点、最近阅读节点和公开推荐起点。

### 页面体验

- 节点页：记录最近阅读，显示进度，可逐节标记完成，并支持节点完成、重新学习和收藏。
- 学习页：显示继续学习、最近阅读，并在图谱标记学习中/已完成节点。
- 首页：登录用户显示继续学习入口。
- 设置页：显示学习概览、继续学习、节点进度、最近阅读和收藏管理。
- 用户状态接口失败时，公开学习内容仍可正常浏览。
- 最近阅读支持分页加载、本地相对时间与精确时间提示；节点错误态提供明确重试入口。
- 前端学习调用集中到 `learning-api.js`，页面和用户状态模块不再散落 API 路径。
- 已删除未被生产页面引用的 `home.js/learn.js/node.js/roadmap.js/tools.js/layout.js` 旧链路；首页、学习总览、节点页和工具页均使用显式页面入口，学习前端不再双轨运行。

## 服务边界

```text
Learning facts and rules
  <- Users learning_state references stable slugs/IDs
  <- Frontend reads public facts
  <- Agent uses read-only adapters

Users learning_state
  -> owns user_id, progress, activity, favorites and resume selection
  -> calls Learning read facade for current titles, links and availability
```

Learning 不依赖 Users；Agent 不直接访问两者的数据表。

## 数据迁移

迁移文件：

```text
database/migrations/001_user_learning_state.sql
database/migrations/002_learning_sections_and_relations.sql
database/migrations/003_learning_content_governance.sql
```

应用启动时通过 `schema_migrations` 记录已经执行的迁移。`schema.sql` 同时保留新表定义，保证全新数据库初始化后结构完整。

## 验证结果

- `scripts/verify-learning.ps1`：通过。
- `python -m unittest discover -s tests -v`：12 项通过。
- `node --test tests/test_learning_frontend.mjs`：2 项通过。
- Python `py_compile`：通过。
- 生产 JS `node --check`：通过。
- Learning HTTP 搜索与节点接口：通过。
- 用户活动、进度、收藏和 dashboard HTTP 流程：通过。
- Playwright 桌面链路：节点 40% -> 标记完成 100% -> 学习页/首页/设置页同步更新，通过。
- Playwright 390x844：无横向溢出，继续学习和知识图谱正常显示。
- 浏览器控制台：无相关 error/warning。
- Playwright 章节链路：0% -> 完成首节 25% -> 并发冲突恢复，桌面与 390x844 移动视口通过。
- `tests/contracts/learning_contract_v1.json` 契约快照已建立；Learning 专项脚本由仓库根目录 `.github/workflows/ai-nav-foundation-ci.yml` 的统一非 Agent 门禁执行。
- 内容门禁验证 104 条已发布引用；本地 100 样本性能基线 p50 约 1.9ms、p95 约 3ms。
- 公开学习 GET 响应具备请求 ID、`Server-Timing` 与短时缓存策略；学习访问日志包含操作、延迟、状态和访问者类型。

## 企业级加固

- Learning 和 Users 学习状态接口均已绑定严格 Pydantic 响应模型，额外字段会被拒绝。
- OpenAPI 明确描述正常、未找到、并发冲突和业务校验响应。
- 请求校验统一返回 `REQUEST_VALIDATION_ERROR`，业务错误使用稳定 code。
- 学习 URL 仅允许 `http/https`，搜索词、slug、幂等键和 metadata 均有限制。
- SQLite 启用 foreign keys、busy timeout 和 WAL；写事务失败会显式回滚。
- 迁移保存 SHA-256 checksum，已经执行的迁移发生漂移时启动失败。
- 进度更新使用版本号和原子写事务，防止多页面静默覆盖。
- 进度和收藏写入与用户审计日志在同一事务提交。
- 阅读活动支持幂等重放标记，最近阅读与收藏分页返回 `totalCount/hasNext`。
- 前端能够识别 `PROGRESS_CONFLICT`，重新加载服务器状态并给出可见提示。
- 章节进度使用独立版本号和 `SECTION_PROGRESS_CONFLICT`，节点总进度按当前有效章节数原子计算。
- 收藏和进度操作具有保存中、成功和错误状态，异步按钮状态不会漂移。

## 完成边界与后续分区

学习区服务地基、用户学习状态和当前 Web 体验已经完成本轮收口。以下工作属于后续独立分区，不在学习核心继续耦合实现：

- 内容运营/管理区：资料审核、发布、归档、质量复核和在线链接巡检界面。
- Agent 区：基于只读学习事实生成计划与解释；任何用户状态写入仍调用 Users 命令接口。
- 平台基础设施：跨服务统一限流、集中指标、告警和分布式缓存。
