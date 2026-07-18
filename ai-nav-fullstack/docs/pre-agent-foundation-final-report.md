# Agent 冻结期地基最终归档

归档日期：2026-07-15

> 后续决策：本报告保留归档时的冻结状态。归档完成后，用户已明确按照 `docs/agent-development-handoff.md` 与 `docs/agent-delivery-roadmap.md` 启动 Agent 专项并持续推进到发布收口。

## 1. 结论

非 Agent 地基已完成本阶段落地与验收：Platform、Learning、Users/Auth、Users Learning State、Tools 和五个普通页面均有明确所有权、单一运行事实源、验证脚本和回滚资料。

Agent 仍按用户决定保持冻结。本报告不代表开始模型 Provider、流式会话、长期记忆、多 Agent 或跨页面 Agent UI；后续必须由用户明确启动新的 Agent 规划阶段。

## 2. 当前版本与规模

| 项目 | 归档值 |
| --- | --- |
| 数据库迁移 | 17 个，checksum 全部登记 |
| Learning | 16 节点、16 主资料、64 目录项、88 补充链接、104 条公开引用 |
| Tools | 136 条保留事实；134 条公开、2 条归档；136 条公开 placement；12 个最新位 |
| 内容链接 | 238 条公开链接；最终显式写回为 216 healthy、22 degraded、0 unavailable |
| Users | 42 项专项测试；28/0/0 安全基线；33 个写命令安全登记 |
| Frontend | 5 个非 Agent 页面唯一入口；21 项前端契约 |
| Runtime | `http://127.0.0.1:8094`，readiness `ready`，migrationCount `17` |

归档时 CodeBuddy 与万彩 AI 已迁移到可达官方入口；Tome Slides 和火山写作保留稳定标识并归档，不再进入公开目录。

## 3. 验收证据

- `verify-foundation.ps1`：非 Agent 发布总门禁，顺序执行 Frontend、Tools、Learning/Platform 和 Users/Release Safety；Foundation CI 对所有代码、迁移、脚本和测试变更执行同一入口。
- `verify-learning.ps1`：聚合 Python 测试、前端学习测试、104 条 Learning 引用、238 条跨域链接门禁和性能基线。
- `verify-tools.ps1`：目录迁移确定性、不可变基线、仓储/search/Agent 只读上下文、前端语法和数据审计。
- `verify-users.ps1`：认证与 Users 测试、安全基线、命令安全、契约冻结、17 迁移备份恢复、性能预算和最终验收报告。
- `verify-frontend.ps1`：页面入口、共享无障碍基线、API 超时/取消/重试、安全链接和共享反馈。
- Playwright：保留五页在 360/768/1440 共 15 个组合的完整基线；最终复核另覆盖 4 个公开页面 x 3 档视口共 12 个页面组合，均无水平溢出、框架错误遮罩或未解释控制台错误。登录态设置页另完成桌面与移动端账号绑定布局，以及注册手机号、联系方式密码确认、邮箱登录和手机号登录的真实交互验证。
- Opera Browser Connector：在真实 Opera 中完成首页读取与截图，页面身份、主要内容、`16+ / 134 / 5 / 3` 统计和最新工具官方外链均可读取。
- 内容在线巡检先预览、再显式写回最后核验时间，最终为 216 healthy、22 degraded、0 unavailable；瞬时网络错误、限流和 5xx 只记为 degraded，不会自动禁用内容。

## 4. 最终归档判定

- 2026-07-15 执行 `verify-foundation.ps1` 全量通过：Frontend 21 项、Tools 6 项、Learning/Platform 72 项 Python 测试与 2 项前端时间戳测试、Users 42 项。
- 迁移备份恢复完整性为 `ok`，外键错误 0，17 个迁移 checksum 一致；Users 安全基线为 28/0/0，33 个写命令完成安全登记。
- Learning 保持 104 条公开引用和 238 条跨域链接门禁；Learning 查询 p95 为 5.845 ms，Users 登录 p95 为 83.940 ms，8 类操作均在预算内且 3 项查询计划通过。
- 登录弹窗默认显示站点 Logo；成功读取登录用户资料后记忆同源头像 URL，退出后仍用于下次登录提示。注册支持可选手机号，账号页支持修改邮箱和手机号，联系方式变更需当前密码并重置验证状态；显式协议同意、撤回后重新授权、保持登录 Cookie 轮换和业务 401 不重放均有回归测试。
- 当前运行时 `http://127.0.0.1:8094` readiness 为 `ready`，migrationCount 为 `17`。
- 非 Agent 地基、验证和归档已完成；Agent 保持冻结，不因本次归档自动解冻。

## 5. 回滚与维护

- 数据库备份、验证和原子恢复：`docs/users-release-runbook.md`。
- 内容输入、追加迁移、在线巡检、归档和恢复：`docs/content-operations-runbook.md`。
- 已执行迁移不可修改；修复和回滚均使用更高版本追加迁移。
- Learning/Tools 公开读取不依赖 Users 或 Agent；关闭 Agent 不影响普通学习与工具页。

## 6. 已知限制与延期项

- 22 条 degraded 链接当前可解释为鉴权、限流、拒绝探测或瞬时网络错误；外链状态具有时效性，应按发布批次复检。
- 浏览器验收已使用 Opera Browser Connector 进行真实 Opera 页面读取与截图，并使用 Chromium Playwright 覆盖自动交互和多视口矩阵；尚未覆盖 Firefox、WebKit 和真实移动设备。
- 大型页面内联 CSS 可继续渐进迁移，但不阻塞当前功能、所有权或 Agent 地基。
- Agent 自身的模型接入、会话、流式输出、长期记忆、评测集和 Agent 页面重构全部延期，未在本阶段宣告完成。
