# ADR：Agent 阶段 1 中国大陆 Provider 与模型策略

状态：已接受模型策略；真实流量仍未授权

决策日期：2026-07-20

## 决策

- 阶段 1 使用阿里云百炼 Model Studio 的华北 2（北京）地域，沿用项目现有 OpenAI-compatible Provider adapter。
- 唯一默认模型是 `qwen3.5-flash`。
- 预留 `qwen3.7-plus` 升级模型配置，但升级比例默认且强制为 `0`。
- 只有版本化评估证明升级模型带来明确收益，并通过成本、安全和引用门槛后，才允许按 `5% -> 10%` 逐步放量；不得超过 `10%`。
- DeepSeek 不进入阶段 1。它只作为阶段 2 的候选可插拔备用 Provider，接入前需重新评审数据处理条款、成本、故障切换和评估结果。
- Provider 只接收用户当前问题和站内公开证据，不发送身份资料、令牌、私有资产、长期记忆或完整 Users Context。
- 真实 Provider、升级模型和第二 Provider 均必须能够独立关闭；任何失败继续回退现有确定性回答。

## 当前配置语义

```text
AI_NAV_AGENT_PROVIDER=deterministic                  # 当前默认，绝不联网
AI_NAV_AGENT_PROVIDER_MODEL=qwen3.5-flash            # 阶段 1 唯一默认模型
AI_NAV_AGENT_PROVIDER_UPGRADE_MODEL=qwen3.7-plus     # 仅预留
AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO=0                # 未经评估不得提高
AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=0                 # 受控验证前保持关闭
AI_NAV_AGENT_PER_USER_CONCURRENCY=1                  # 每用户在途 Provider 请求
AI_NAV_AGENT_GLOBAL_CONCURRENCY=8                    # 单进程全局在途请求
AI_NAV_AGENT_QUEUE_LIMIT=32                          # 有限等待队列
AI_NAV_AGENT_QUEUE_TIMEOUT_SECONDS=3                 # 超时后确定性回退
AI_NAV_AGENT_PROVIDER_MAX_INPUT_TOKENS=4000
AI_NAV_AGENT_PROVIDER_MAX_OUTPUT_TOKENS=600
AI_NAV_AGENT_PER_REQUEST_COST_CNY=0.02
AI_NAV_AGENT_PER_USER_DAILY_COST_CNY=0.1
AI_NAV_AGENT_GLOBAL_DAILY_COST_CNY=5
AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY=80
```

## 上线前待办

人工签收和证据位置统一记录在 `docs/04-operations/agent/agent-provider-stage1-release-checklist.md`。

- [x] 在产品界面和 `2026-07-20` 隐私政策中完成第三方模型处理告知；使用现有版本化 `privacy_policy` 重新确认，不新增与长期记忆混淆的同意类型。
- [x] Provider 调用前检查当前版本隐私同意；未同意、旧版本或撤回后仅返回站内确定性回答。
- [ ] 【上线前处理】签署或确认数据处理协议、调用数据留存期限、不用于训练承诺及删除协助机制。
- [x] 已落实进程内每用户/全局并发、有限排队、Token 与日/月成本保护；超限时返回确定性回答。
- [ ] 【上线前处理】在供应商账户落实余额不自动充值和不高于 100 元的账户硬上限；应用内账本不能替代供应商侧硬限额。
- [ ] 【上线前处理】创建独立、可撤销的生产 API Key，并配置北京默认业务空间专属域名及上海生产主机允许列表。
- [ ] 【上线前处理】使用临时凭据执行受控真实验证；不得进入默认 CI，不得记录 Prompt、响应正文或密钥。
- [ ] 【上线后评测】以同一评估集比较 deterministic、`qwen3.5-flash` 与 `qwen3.7-plus`，记录质量增益、延迟和实际 Token 成本。
- [ ] 【上线后评测】只有评估结论获批后，才允许 `qwen3.7-plus` 的 5% 灰度；当前路由能力已接好且比例固定为 0%。
- DeepSeek 是阶段 2 的证据触发可选扩展，不是当前版本欠账；在需要第二 Provider 的评估证据出现前不增加其密钥、路由或运行依赖。

## 运行限制

- 当前治理账本只存在于 API 进程内，重启后清零；阶段 1 生产部署必须保持单 API worker。
- 如果未来启用多 worker 或多实例，应在不改变 Agent 编排契约的前提下，把治理 adapter 替换为共享存储实现。
- 应用阈值是快速降级保护，不是财务硬限额；真正的总费用硬上限依靠供应商余额、不自动充值和账单告警。

## 回滚

将 `AI_NAV_AGENT_PROVIDER_LIVE_ENABLED` 设为 `0` 或将 `AI_NAV_AGENT_PROVIDER` 设为 `deterministic`。回滚不涉及数据库迁移和用户数据修复。
