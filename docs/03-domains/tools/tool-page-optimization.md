# 工具区优化与维护指南

## 1. 定位

Tools 是模块化单体中的一个内聚功能域，为 Web、站内搜索和未来 Agent 提供统一的工具事实、分类关系、运营位与检索能力。

本项目体量下不拆分 catalog、category、collection、link 或 capability 微服务。默认结构保持：

```text
router -> service -> repository -> SQLite
```

只有出现真实外部系统或多种存储实现时，才增加适配器或 port。

## 2. 所有权

| 内容 | 所有者 | 消费方 |
| --- | --- | --- |
| 工具名称、别名、描述、官网、图标、免费标记 | Tools | Web、Search、Agent |
| 分类和子分类 | Tools | Web、Search、Agent |
| 工具在分类中的 placement、热度和标签 | Tools | Web、Search、Agent |
| 最新上架运营位 | Tools | Web、Agent |
| 用户的免费优先、国内优先偏好 | Users | Tools/Web 只读消费 |
| 推荐解释、对话、计划和确认 | Agent | Web |

Agent 不读取工具页 DOM、不导入前端迁移快照、不查询 Tools 表。它通过 `app.tools.service` 的只读能力获取事实，并在 Agent 自己的编排层生成解释。

## 3. 当前运行链路

- 数据库是运行时唯一事实源。
- `backend/app/tools` 负责读取、聚合、搜索和工作流候选。
- `backend/app/api/v1/routers/tools.py` 只做 HTTP 参数与响应映射。
- `frontend/assets/js/tools-page.js` 是工具页唯一渲染入口。
- `frontend/assets/js/site-search.js` 优先读取 Tools API，不维护第二份工具目录。
- `tool-data.js` 和 `tool-page-lists.js` 只保留为历史目录迁移输入及对账基线，不被运行时页面加载。

## 4. 数据结构

- `ai_tools`：工具事实和兼容字段。
- `tool_categories` / `tool_subcategories`：分类事实。
- `tool_placements`：多分类展示关系、热度和标签。
- `tool_latest_slots`：最新上架运营位。

暂不继续拆 aliases、icons、links、capabilities 子表。当前 JSON 字段和 placement 标签足以支撑项目规模；后续只有在独立维护、查询或权限需求出现时再规范化。

## 5. 目录更新流程

已执行的迁移必须保持不可变。`010_tool_catalog_source_of_truth.sql` 是初始全量迁移，不能重新生成覆盖。

更新工具目录时：

1. 修改迁移输入快照并运行静态审计。
2. 使用一个高于现有版本的新文件生成迁移，例如：

```powershell
python scripts/generate-tool-catalog-migration.py --output database/migrations/013_tool_catalog_refresh.sql
```

3. 检查生成 diff，确认失活、placement 和最新运营位变化符合预期。
4. 在临时数据库执行全部迁移。
5. 运行 `verify-tools.ps1` 和运行时字段级对账。

生成器拒绝覆盖已有迁移，也不再把 136/138 固定为永久业务规则。

## 6. 前端规则

- 分类、卡片、最新运营位和免费状态来自 `/api/v1/tools/catalog`。
- API 不可用时显示明确错误和重试，不静默加载旧快照。
- URL 中的 `q` 参数由工具页在 catalog 就绪后应用，不能依赖固定延时派发事件。
- 页面中的多个同义筛选入口必须共享一个状态并同步 `aria-pressed`。
- “免费优先”只依据 Tools 的 `isFree` 事实，不把“国产”或“中文”混入免费语义。

## 7. Agent 演进边界

当前保留 `search_tools`、`workflow_suggestions` 和紧凑 Agent context 作为只读地基。后续 Agent 阶段可以增加稳定 schema、引用与评估集，但遵循：

- Tools 返回事实和确定性排序，不保存会话。
- Agent 负责意图理解、组合、解释和确认。
- 用户工作流保存走 Users Assets，不写回 Tools。
- 不为了未来可能性提前创建多个空服务或 provider 层。

## 8. 验收

```powershell
.\scripts\verify-tools.ps1
$env:AI_NAV_BASE_URL='http://127.0.0.1:8094'
node scripts/audit-tool-data.mjs
```

验收覆盖迁移完整性、生成器确定性、不可变基线、字段级运行时对账、图标与 URL、搜索、免费筛选、前端语法和浏览器交互。
