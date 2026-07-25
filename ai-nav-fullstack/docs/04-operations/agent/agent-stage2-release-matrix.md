# Agent 阶段 2 发布开关矩阵

本文只描述当前代码已经支持的组合。任何组合都不能绕过真实 Provider 上线清单、隐私同意、成本上限和单 worker 约束。

管理员可通过 `GET /api/v1/agent/operations/runtime` 查看脱敏运行快照。接口只返回 Provider 模式、模型别名、功能开关、安全约束和拓扑，不返回 API Key、Provider 地址、允许主机或内部配置错误。

## 允许组合

| 场景 | Provider | Live | SSE | Sessions | 结果 |
| --- | --- | ---: | ---: | ---: | --- |
| 默认安全基线 | `deterministic` | 0 | 0 | 0 | 普通 JSON、无模型调用、无会话持久化 |
| 仅验证 SSE | `deterministic` | 0 | 1 | 0 | 从标准响应安全投影 SSE |
| 仅验证短期会话 | `deterministic` | 0 | 0 | 1 | 显式创建后保存最小问答 |
| 阶段 2 离线全功能 | `deterministic` | 0 | 1 | 1 | 可验证流式传输、停止、重试和会话，不产生模型费用 |
| Fake 测试 | `fake` | 0 | 任意 | 任意 | 仅限开发和测试；生产拒绝 |
| Provider 已配置但关闭 | `openai_compatible` | 0 | 任意 | 任意 | 校验 Key/地址/模型，但不实例化真实 Provider |
| 阶段 1 受控调用 | `openai_compatible` | 1 | 0 | 0 | 完整 JSON；仅在上线清单全部签收后允许 |
| 阶段 2 受控 SSE | `openai_compatible` | 1 | 1 | 任意 | 当前百炼 adapter 仍为安全缓冲投影，不宣称 token 级增量 |
| 阶段 2 受控会话 | `openai_compatible` | 1 | 任意 | 1 | 只有显式会话保存最终验证后的最小问答 |

所有允许组合仍满足：

- `qwen3.5-flash` 是唯一默认模型；
- `qwen3.7-plus` 升级比例为 0；
- 浏览器断线不会自动再次请求模型；
- 完成响应重放和管理员指标始终启用；
- Provider 调用前要求当前隐私政策版本的有效同意；
- `AI_NAV_API_WORKERS=1` 且状态后端为 `process_local`。

## 明确拒绝组合

| 组合 | 拒绝原因 |
| --- | --- |
| `deterministic` + Live 1 | 开关与实际 Provider 不一致，可能造成错误上线判断 |
| `fake` + Live 1 | Fake 不是实时 Provider |
| 生产环境使用 `fake` | 测试实现不得进入生产 |
| 多 worker + `process_local` | 治理、重放和指标会分裂 |
| 未实现的共享状态后端 | 当前没有可验证的共享 adapter |
| 升级比例大于 0 | 尚无获批的模型评测结论 |
| 实时模型不是 `qwen3.5-flash` | 违反阶段 1 模型决策 |
| 生产 Provider 主机未进入允许列表或不是北京专属域名 | 违反地域和出站边界 |

短期会话开关打开但迁移 018 未应用时，数据库 readiness 会失败；它不是可降级的允许组合。

Provider 组合无效时，Provider 装配被拒绝并返回确定性结果，整站继续可用；
管理员运行快照显示 `invalid`。单 worker 拓扑和生产安全配置错误属于启动级错误，
不会降级放行。

## 推荐启用顺序

1. 固定单 worker、`process_local`、`deterministic`、Live 0。
2. 单独打开 Sessions，完成新建、恢复、删除和保留期验证。
3. 单独打开 SSE，完成停止、背压、断线人工重试验证。
4. 组合 SSE 与 Sessions，继续保持 deterministic。
5. 将 Provider 改为 `openai_compatible`，Live 仍为 0，核对脱敏运行快照。
6. 最终上线清单全部签收后，短时打开 Live 进行受控验证。
7. 验证结束立即将 Live 恢复为 0；未获生产授权时不得保留实时调用。

## 回滚顺序

出现费用、安全、延迟或供应商异常时，第一步始终是
`AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=0`。随后按需要关闭 SSE 和 Sessions，最后将
Provider 恢复为 `deterministic`。这些操作不需要回滚数据库迁移，已保存的短期会话仍按保留期和用户删除规则处理。

## 可重复发布演练

在项目根目录运行：

```powershell
$env:PYTHONPATH = "backend;.venv\Lib\site-packages"
python scripts/rehearse-agent-stage2.py
```

脚本不会读取或调用真实 Provider：它在子进程导入应用前显式设置 `deterministic`、Live 0、空 Provider Key/地址/允许主机，并为启用档案和回滚档案分别创建临时数据库。

2026-07-24 基线结果为 29/29 项通过，覆盖：

- readiness 与迁移 018；
- 管理员脱敏运行快照；
- SSE started/delta/completed；
- 短期会话新建、读取、幂等重试和删除；
- 同一 `X-Request-Id` 的人工断线重试；
- 关闭 SSE/Sessions 后端点拒绝且 JSON 回答继续可用；
- qwen3.5-flash 默认模型与 qwen3.7-plus 0% 升级比例。

机器可读基线见 `docs/06-evidence/agent/agent_stage2_release_rehearsal.json`。该结果是 deterministic 离线发布证据，不是生产容量或真实 Provider 上线授权。
