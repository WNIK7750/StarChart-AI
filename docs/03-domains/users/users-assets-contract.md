# Users 用户资产契约

## 所有权边界

- Users 是用户工作流、学习计划及其他私人资产的唯一事实来源；当前批次实现 `user_saved_workflows`，学习计划沿用同一边界但尚不扩展存储模型。
- Agent、Learning 和 Tools 只能调用 Users facade/API，不得查询或写入用户资产表。
- Agent 负责生成可保存草稿，Users 负责确认校验、幂等、版本控制、持久化和审计。替换 Agent 编排框架不得改变资产结构。

## 稳定引用

- 工作流以 `workflow_uid` 对外，步骤以 `step_uid` 对外；数据库自增 ID 不进入跨域契约。
- 工具目标使用稳定 `toolSlug`，并保存名称与链接快照。目标下线时返回 `target.status=unavailable` 和工作流 `availability.status=degraded`，不删除步骤或工作流。
- 工具引用不设置级联外键，避免领域内容下线破坏用户私人资产。

## 写入规则

- 创建必须携带 `confirmed: true` 和 `Idempotency-Key`；同一用户重复提交相同幂等键返回原资产且不重复审计。
- 更新、归档和恢复必须携带 `expectedVersion`；过期版本返回 `409 WORKFLOW_VERSION_CONFLICT`。
- 删除语义统一为归档；当前 API 不提供物理删除。

## API

- `GET/POST /api/v1/users/me/assets/workflows`
- `GET/PATCH /api/v1/users/me/assets/workflows/{workflowUid}`
- `POST /api/v1/users/me/assets/workflows/{workflowUid}/archive`
- `POST /api/v1/users/me/assets/workflows/{workflowUid}/restore`
- `POST /api/v1/agent/workflows/save`：仅接受 `sourceType=agent`，并委托 Users command facade。

列表响应包含 `page`、`pageSize`、`totalCount` 和 `hasNext`。所有读写按认证用户隔离，资产写入事件登记在 `docs/03-domains/users/users-audit-event-catalog.md`。

## Agent 上下文

`UserContextFacade.for_agent()` 只提供偏好、能力布尔值和资产数量/最近摘要，不暴露角色、认证秘密或完整资产内容。Agent `/chat` 返回的 `workflowDraft` 与 Users 创建 DTO 对齐，调用方只需在明确确认后补充 `confirmed: true` 并生成幂等键。
