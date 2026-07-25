# Tools 模块实施记录

## 边界

Tools 是模块化单体中的一个内聚模块，负责工具事实、分类展示关系、最新运营位、
搜索和 Agent 上下文。它不拆分为多个可部署服务，也不为分类、别名或链接创建独立分层。

## 数据模型

- `ai_tools`：136 条保留工具事实，包含别名、描述、官网、图标、发布状态和链接状态；当前公开 134 条、归档 2 条。
- `tool_placements`：保留 138 条多分类关系，公开目录读取 136 条已发布工具关系。
- `tool_categories` / `tool_subcategories`：7 个活动顶层分类及子分类。
- `tool_latest_slots`：12 个版本化最新工具展示位。
- `ai_tools.publication_status/link_status/last_checked_at`：发布生命周期与外链巡检事实；失效链接保留工具事实但禁用前端外跳。

`010_tool_catalog_source_of_truth.sql` 由 `scripts/generate-tool-catalog-migration.py` 确定性生成。
前端 JS 快照是本次迁移输入，不再被后端、页面或站内搜索在运行时导入。

`010` 已作为不可变基线冻结。后续目录更新必须用生成器的 `--output` 创建更高版本迁移，生成器拒绝覆盖已有迁移，也不再固定工具和 placement 数量。`011_tool_catalog_integrity_cleanup.sql` 清理旧失活分类下的子分类并统一免费/开源标记，`012_tool_catalog_refresh.sql` 用追加迁移修正历史 Sentry 分类乱码。

## 运行链路

- Tools 页读取 `GET /api/v1/tools/catalog`。
- 站内搜索索引读取同一 catalog API，查询读取 `/tools/search`。
- Agent tool adapter 直接调用 `app.tools.service`。
- API 不可用时，Tools 页显示可重试错误，不静默回退到过期快照。
- `tools-page.js` 是工具页唯一渲染入口；`v2-api.js` 不再保留第二套工具目录渲染逻辑。
- URL 查询参数在 catalog 完成后应用，多个“免费优先”入口共享同一状态。

## 验证

```powershell
.\scripts\verify-tools.ps1
$env:AI_NAV_BASE_URL='http://127.0.0.1:8094'; node scripts/audit-tool-data.mjs
```

验证覆盖数据迁移计数、外键、不可变迁移、生成确定性、数据库搜索、字段级运行时对账、前端语法与浏览器故障态。

跨域内容链接的离线门禁和显式在线巡检见 `docs/04-operations/content/content-operations-runbook.md`。Tools 不为链接治理拆出独立服务。

Tools 继续作为未来 Agent 的只读事实模块，但不承载对话、会话、模型 provider 或用户资产写入。相关编排留在 Agent，用户保存留在 Users Assets。
