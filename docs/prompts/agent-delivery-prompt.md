# Agent 后续开发任务启动提示

你负责 `ai-nav-fullstack` 的 Agent 专项开发，目标是按照既定顺序持续推进到发布收口，而不是只输出建议或一次性堆叠所有 Agent 能力。

开始前按顺序阅读：

1. `docs/pre-agent-foundation-final-report.md`
2. `docs/agent-development-handoff.md`
3. `docs/agent-delivery-roadmap.md`
4. `docs/agent-service-implementation.md`
5. `docs/modular-monolith-guidelines.md`
6. `docs/agent-design.md`

执行要求：

- 先运行 `scripts/verify-foundation.ps1` 和 `scripts/verify-agent.ps1`，再从路线图中第一个未完成 Phase 继续。
- 当前确定性 Agent 是稳定契约、测试基准和离线回退，不要推倒重写。
- Agent 是模块化单体中的编排域，只调用 Learning、Tools、Users 的公开能力，不直接访问领域表。
- 用户写操作必须经过对应 Users command facade，并具备显式确认、授权、幂等、审计和失败恢复。
- 优先完成一个用户可见纵向闭环；不要提前拆微服务、引入内部 HTTP、消息队列、多个 planner/retriever/memory 子服务。
- 模型 Provider 是合理的外部边界，但供应商 SDK 类型不得泄漏到公共 API、领域工具或前端。
- Prompt 不能承载权限、链接、幂等或业务事实校验；这些规则必须由代码执行。
- LangGraph、向量库、长期记忆、第二 Provider 和多 Agent 只有满足交接文档中的触发条件后才引入。
- 新增迁移只能追加，不能修改已经应用的迁移。
- 每次实现都补齐正常、失败、安全和回退测试；涉及 UI 时完成真实浏览器与多视口验证。
- 每轮结束更新 `docs/agent-delivery-roadmap.md` 的状态和阶段记录，写清契约、迁移、验证、回滚、风险和下一任务。
- 保持非 Agent Foundation 总门禁持续通过；Agent 可关闭且不得影响 Learning、Tools、Users 的普通体验。

当前下一任务：执行 Phase 1，增加可注入模型 Provider 边界和真实模型只读回答，并保留 deterministic 回退。不要在同一轮提前实现会话、长期记忆、状态图或多 Agent。

