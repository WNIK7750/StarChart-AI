# Agent 阶段 5 发布与回滚手册

## 发布边界

当前仅允许发布默认关闭真实 Provider 的版本。`qwen3.5-flash` 是唯一默认模型，`qwen3.7-plus` 升级比例固定为 `0`。在供应商协议、上海服务器出站白名单、专属域名、费用限制和受控真实验证全部签收前，不得开启生产实时调用。

Agent 继续位于模块化单体内，通过领域 service/facade 调用 Learning、Tools、Navigation 和 Users；关闭 Agent 或 Provider 故障不得影响普通页面和公开读取能力。

## 功能开关

| 能力 | 安全发布值 | 启用前条件 | 回滚值 |
| --- | --- | --- | --- |
| Provider | `AI_NAV_AGENT_PROVIDER=deterministic` | 上线清单全部签收后才改为 `openai_compatible` | `deterministic` |
| 真实调用 | `AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=0` | 受控验证窗口与回滚负责人就绪 | `0` |
| SSE | `AI_NAV_AGENT_STREAM_ENABLED=0` | 浏览器停止、断线与重试验收通过 | `0` |
| 短期会话 | `AI_NAV_AGENT_SESSIONS_ENABLED=0` | migration 018、删除与保留期验收通过 | `0` |
| 模型升级 | `AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO=0` | 脱敏配对评测给出人工放量建议 | `0` |
| 运行状态 | `AI_NAV_AGENT_RUNTIME_STATE_BACKEND=process_local` | 仅允许单 API worker | `process_local` |

开关组合和拒绝条件以 `agent-stage2-release-matrix.md` 为准。发布过程不得自动修改模型升级比例。

## 已知限制

- 进程内重放、成本账本和聚合指标不跨 worker，生产拓扑固定为单 API worker。
- 当前百炼 adapter 对 SSE 使用安全缓冲投影，不声明真实 token 级增量。
- 短期会话只在用户显式创建并携带 `sessionId` 后保存；匿名对话不会自动持久化。
- 长期记忆保持关闭。
- 阶段 5 已完成 Chromium、Firefox、WebKit 与 Opera 的 390×844 移动视口验证，并通过 Pixel 7 与 iPhone 15 设备仿真；真实移动设备与读屏软件仍是发布前验收项。
- 离线性能基线不包含真实 Provider 网络延迟，不构成上海服务器生产容量承诺。

## Provider 数据边界

Provider 请求只允许包含当前问题、受限系统指令和站内公开证据包。不得发送账号资料、Authorization、Cookie、API Key、工作流资产明细、长期记忆或其他用户私有数据。调用前必须存在当前 `privacy_policy` 版本的有效同意。

请求 trace 只记录散列请求标识、模式、Provider、模型、尝试、回退、校验错误、Prompt 版本、证据数、实际只读工具、耗时、Token 和成本；不得记录问题、回答或用户身份。

## 并发与成本阈值

阶段 1 默认值：

| 约束 | 环境变量 | 默认值 |
| --- | --- | ---: |
| 每用户并发 | `AI_NAV_AGENT_PER_USER_CONCURRENCY` | 1 |
| 全局并发 | `AI_NAV_AGENT_GLOBAL_CONCURRENCY` | 8 |
| 有限队列 | `AI_NAV_AGENT_QUEUE_LIMIT` | 32 |
| 排队超时 | `AI_NAV_AGENT_QUEUE_TIMEOUT_SECONDS` | 3 秒 |
| 单请求成本 | `AI_NAV_AGENT_PER_REQUEST_COST_CNY` | 0.02 元 |
| 每用户每日成本 | `AI_NAV_AGENT_PER_USER_DAILY_COST_CNY` | 0.1 元 |
| 全局每日成本 | `AI_NAV_AGENT_GLOBAL_DAILY_COST_CNY` | 5 元 |
| 全局每月成本 | `AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY` | 80 元 |

供应商侧费用限制不得高于应用内上限形成的发布预算；正式值必须在受控真实验证后按实测 Token 与请求分布复核。

## 发布前门禁

1. 运行 `scripts/verify-agent.ps1` 和 `scripts/verify-foundation.ps1`。
2. 运行 `scripts/rehearse-agent-stage2.py`，确认启用档案和回滚档案均通过。
3. 按 `docs/04-operations/users/users-release-runbook.md` 验证迁移、备份、恢复、安全与性能门禁。
4. 核对 Agent 页面在 Chromium、Firefox、WebKit、Opera 和真实移动设备上的会话、停止、重试、引用、确认、错误恢复、键盘、焦点、读屏、长文本、窄屏与 reduced motion。
5. 真实 Provider 保持关闭时检查 `/api/v1/health/live`、`/api/v1/health/ready`、普通页面、公开 Learning/Tools 和确定性 Agent。
6. 仅在 `agent-provider-stage1-release-checklist.md` 全部签收后执行一次受控真实验证；结束后立即把 Live 恢复为 `0`。

任一门禁失败即停止发布，不以“仅 Agent 有问题”为由放行。

真实设备与读屏的隔离验收步骤见 `agent-real-device-screen-reader-checklist.md`；该流程不使用数据库、真实 Provider 或 API Key。

## 监控与告警

- 管理员检查 `GET /api/v1/agent/operations/runtime`，确认 Provider、模型、开关和单 worker 拓扑与发布档案一致。
- 管理员检查 `GET /api/v1/agent/operations/metrics`，观察请求、Provider 尝试、回退、校验失败、重放冲突、延迟、Token 和成本。
- 观察 `/api/v1/health/live` 与 `/api/v1/health/ready`、HTTP 5xx、认证失败和普通页面可用性。
- 成本或并发拒绝异常上升、Provider 回退持续发生、校验失败、安全/引用失败或非 Agent 页面受影响时立即回滚。
- 日志和归档不得包含 API Key、Provider 原始响应、问题、回答或用户身份。

## 回滚与故障演练

1. 将 `AI_NAV_AGENT_PROVIDER_LIVE_ENABLED` 设为 `0`。
2. 视故障范围关闭 SSE 与 Sessions。
3. 将 Provider 恢复为 `deterministic`，保持 `qwen3.7-plus` 比例为 `0`。
4. 重新检查 live/ready、普通页面、公开 Learning/Tools 和确定性 Agent。
5. 保留已写入的短期会话并继续执行保留期和用户删除规则；不执行破坏性 down migration。
6. 若普通功能仍异常，按 `docs/04-operations/users/users-release-runbook.md` 回滚应用版本并使用发布前备份恢复。

故障演练至少覆盖 Provider 超时/不可用、无效输出、SSE 关闭、Sessions 关闭和完全关闭真实 Provider。脱敏演练记录不得包含用户内容或凭据。

## 当前可复现证据

- 阶段 2 启用/回滚演练：`docs/06-evidence/agent/agent_stage2_release_rehearsal.json`
- 阶段 3 工作流幂等与详情演练：`docs/06-evidence/agent/agent_stage3_workflow_save_rehearsal.json`、`agent_stage3_workflow_detail_rehearsal.json`
- 阶段 4 离线完成审计：`docs/06-evidence/agent/agent_stage4_completion_audit.json`
- 阶段 5 体验审计：`docs/06-evidence/agent/agent_stage5_experience_audit.json`
- Provider 上线签收：`docs/04-operations/agent/agent-provider-stage1-release-checklist.md`

这些证据允许复现离线发布与回滚，不代表真实 Provider、上海容量或生产合规已经获批。
