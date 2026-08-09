# 图表索引

[打开可编辑 FigJam 总图](https://www.figma.com/board/i0pcIRwKa0aKG0KxTXFvox)

| 图 | 图源 |
| --- | --- |
| 物理部署拓扑 | [01-physical-architecture.mmd](./01-physical-architecture.mmd) |
| 模块化单体领域边界 | [02-domain-boundaries.mmd](./02-domain-boundaries.mmd) |
| Agent 单次请求节点流 | [03-agent-request-flow.mmd](./03-agent-request-flow.mmd) |
| Agent 登录请求时序 | [04-agent-sequence.mmd](./04-agent-sequence.mmd) |
| 模型实验与发布门禁 | [05-model-experiment-gate.mmd](./05-model-experiment-gate.mmd) |
| Agent 会话数据模型 | [06-agent-session-erd.mmd](./06-agent-session-erd.mmd) |
| Agent 受控证据循环架构 | [07-agent-controlled-loop.mmd](./07-agent-controlled-loop.mmd) |

说明：

- FigJam 中的图可直接编辑。
- `.mmd` 是生成时使用的 Mermaid 源，便于版本管理和以后重画。
- “Agent 节点流”是对函数处理阶段的可视化，不代表项目使用 LangGraph。
- “Agent 受控证据循环”中的回边表示工具结果回到编排器形成一次证据反馈，不表示自主多轮 ReAct。
- 物理部署图只画独立部署单元；领域边界图才展开单体内部模块。
