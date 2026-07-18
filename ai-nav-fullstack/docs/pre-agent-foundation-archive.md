# Agent 重启前落地与归档清单

更新时间：2026-07-15

> 后续决策：本文件保留为非 Agent 地基归档快照。用户已明确后续按照 `docs/agent-development-handoff.md` 与 `docs/agent-delivery-roadmap.md` 推进 Agent 专项直到发布收口；这不改变本归档记录的验收事实。

## 1. 当前决定

Agent 保持冻结。现有 `assistant.html`、确定性只读编排和工作流确认保存链路只作为基线保留，不接入模型 Provider、流式响应、会话、长期记忆、多 Agent 或跨页面 Agent UI。

只有本清单中的非 Agent 收口与归档门槛满足后，才重新规划 Agent。

## 2. 已落地模块

| 模块 | 当前状态 | 主要证据 |
| --- | --- | --- |
| Platform | 已落地 | 17 个 checksum 迁移、统一错误/request ID、健康探针、导航完整性测试 |
| Learning | 已落地 | 独立 service/repository、稳定内容 UID、搜索与语义关系、用户无关公开读取、104 个发布引用检查 |
| Users/Auth | 已落地 | 42 项专项测试、28/0/0 安全基线、命令安全登记、备份恢复和性能基线 |
| Users Learning State | 已落地 | 进度、章节、活动、最近阅读、继续学习、收藏、匿名导入、幂等和并发版本 |
| Tools | 已落地 | 数据库唯一运行事实源、136 条保留事实、134 条公开工具、136 条公开 placement、12 个最新位、字段级对账 |
| Frontend | 已落地 | 五个非 Agent 页面唯一入口、旧双轨删除、统一 API 网络边界、共享反馈、URL 白名单、三档视口与键盘验收 |
| Agent | 冻结 | 保留现有确定性基线，不继续建设 |

## 3. 本轮前端与导航证据

- `tests/test_frontend_entries.mjs`：页面入口、旧脚本、静态页面链接和新窗口隔离。
- `tests/test_frontend_api.mjs`：GET 有限重试、写请求不重放、业务 401 不刷新重放、超时和调用方取消。
- `tests/test_frontend_url_safety.mjs`：站内同源和 HTTP/HTTPS 外链白名单。
- `tests/test_frontend_feedback.mjs`：错误文本安全渲染和离线状态。
- `tests/test_platform_navigation.py`：数据库导航只指向真实产品页面。
- `013_navigation_integrity.sql`：助手导航指向 `assistant.html`，删除无内容 About 导航。
- Users 服务/SQL 微基准使用共享内存 SQLite，隔离 Windows 临时文件和杀毒扫描抖动；文件型可靠性由 17 个迁移的备份恢复、完整性、外键和 checksum 演练覆盖。
- 登录与账号维护项已收口：默认站点 Logo、最近登录头像提示、注册可选手机号、用户名/邮箱/手机号登录、邮箱和手机号绑定修改、协议重新授权及保持登录 Cookie 轮换均进入自动化回归；联系方式变更要求当前密码并重置对应验证状态。
- Opera Browser Connector 已用于真实 Opera 页面读取和截图，并确认首页统计及最新工具外链可读；Playwright 保留五个非 Agent 页面在 360、768、1440 视口下的完整基线，最终复核另覆盖 4 个公开页面 x 3 档视口共 12 个页面组合，均无水平溢出、框架错误遮罩或未解释控制台错误。
- 隔离数据库登录态深链路已覆盖学习进度同步、导出脱敏、删除申请/撤销和降级工作流归档，不污染当前开发数据库。
- toast/dialog 复用评估：破坏性确认仅属于设置页，Learning/Tools 已共享状态反馈，没有引入全局框架的真实重复需求。
- `014_content_link_governance.sql` 与 `check-content-links.py`：统一 238 条公开链接的生命周期、健康状态、最后巡检时间和显式写回流程。
- `015_tool_catalog_refresh.sql`：更新两个官方入口，归档两个已终止或无有效入口的工具；最终显式写回巡检为 216 healthy、22 degraded、0 unavailable。
- `content-operations-runbook.md`：固定内容输入、追加迁移、备份、发布、巡检、归档和回滚流程。

## 4. Agent 解冻前剩余任务

非 Agent 落地、全量验证和归档任务已完成，最终证据见 `docs/pre-agent-foundation-final-report.md`。归档完成后的 Agent 专项已形成独立交接和执行路线，不在本历史清单内继续追加实现任务。

## 5. Agent 解冻门槛

必须同时满足：

1. 所有非 Agent 专项验证脚本通过。
2. 浏览器关键流程无高优先级缺陷、无水平溢出、无未解释控制台错误。
3. Learning、Tools、Users 的所有权和公开契约不再漂移。
4. 页面不存在重复渲染者、失效 HTML 链接或第二运行事实源。
5. 数据迁移、备份恢复和回滚资料与当前迁移版本一致。
6. 最终归档明确列出延期项，不以未验证状态宣告完成。

## 6. 当前验证命令

```powershell
.\scripts\verify-foundation.ps1

# 需要定位模块问题时可单独运行：
.\scripts\verify-frontend.ps1
.\scripts\verify-learning.ps1
.\scripts\verify-tools.ps1
.\scripts\verify-users.ps1
```

当前开发验证地址：`http://127.0.0.1:8094`，readiness 为 `ready`，迁移数为 17。
