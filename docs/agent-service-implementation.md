# Agent 第一阶段实施记录

> 后续开发入口：`docs/agent-development-handoff.md`、`docs/agent-delivery-roadmap.md`。本文件只记录当前确定性第一阶段的实现事实。

## 1. 模块边界

Agent 是模块化单体中的编排域，不拥有 Learning、Tools 或 Users 的事实数据。

```text
Agent router
  -> Agent service
      -> Learning read adapter
      -> Tools read adapter
      -> Users Context facade
```

- Learning 返回学习节点、关系和站内引用。
- Tools 返回工具事实、确定性搜索和工作流候选。
- Users Context 只返回允许给 Agent 使用的偏好、能力和资产摘要。
- Agent 负责意图、组合、解释和输出校验。
- 工作流保存继续走 Users Assets 的确认、幂等和审计命令。

不创建独立部署服务，不提前拆 planner、retriever、memory 或 provider 子服务。

## 2. 当前能力

- `POST /api/v1/agent/chat` 使用稳定请求和响应模型。
- 响应包含 `answer`、`intent`、`cards`、`citations`、`toolCalls`、`workflowSteps`、`workflowDraft`、`followups` 和 `meta`。
- 引用和步骤链接只允许站内白名单页面。
- 支持 QA、导航、工具推荐、学习计划和工作流生成意图。
- 无模型时仍可使用确定性检索和规则顺序。
- 当前 `meta.mode` 为 `deterministic`，`readOnly` 为 `true`。

## 3. 产品入口

`frontend/assistant.html` 是真实助手入口，`assistant-page.js` 是唯一页面脚本。桌面采用上下文、对话、证据三栏布局，移动端收敛为单列。

页面支持：

- 中文问题和快捷任务。
- Learning/Tools 站内卡片。
- 引用与实际工具调用记录。
- 学习顺序和工作流草案。
- 工作流保存前显式勾选确认。
- 未登录时调用现有认证入口。

## 4. 安全约束

- Chat 需要 `agent:chat` 权限。
- Agent 不查询 Users 数据表，只调用公开 facade。
- 第一阶段没有自动写入、自动浏览或外部工具执行。
- Agent 输出不能生成外部或未允许的站内链接。
- 工作流草案不等于保存命令；保存必须 `confirmed=true` 并携带 `Idempotency-Key`。

## 5. 后续阶段

以下能力暂不在第一阶段实现：

- 模型 provider port 和真实生成式回答。
- SSE 流式输出与会话持久化。
- 长期记忆和上下文压缩。
- 多 Agent、图编排和自动外部工具调用。
- 完整 QA、导航、推荐、计划、安全和越权评估集。

只有接入真实模型边界时才增加 provider port；只有需要可恢复长任务时再评估状态图框架。

## 6. 验证

```powershell
.\scripts\verify-agent.ps1
.\scripts\verify-users.ps1
.\scripts\verify-learning.ps1
.\scripts\verify-tools.ps1
```

浏览器验收覆盖登录、中文学习问题、工具推荐、引用、工作流草案、未确认不可保存、确认后保存、未登录状态以及桌面/移动端布局。
