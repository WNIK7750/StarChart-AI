# Users 隐私与账号生命周期

## 权威数据

- 隐私政策和 Agent memory 同意以 `user_privacy_consent_events` 的追加事件为准。
- 每个事件包含同意类型、政策版本、grant/revoke 动作、来源和时间。
- 当前隐私政策明确告知：启用模型服务时，仅把当前问题与站内公开证据发送至阿里云百炼千问北京区域处理；账号资料、用户资产、令牌和长期记忆不进入 Provider 请求。
- Agent 调用 Provider 前必须确认 `privacy_policy` 最新事件为 granted 且版本等于当前服务端版本。未同意、旧版本或已撤回时保留站内确定性回答，但不得调用 Provider。
- Agent 只有在 `agent_memory` 最新事件为 granted，且版本等于当前服务端版本时才能获得 memory 上下文。
- `agent_memory` 只授权长期记忆读取，不替代隐私政策中的第三方模型处理告知；隐私政策同意也不会自动开启长期记忆。
- `user_preferences.agent_memory_enabled` 是历史兼容字段，不再单独产生授权效果。

## 数据导出

`POST /api/v1/users/me/privacy/export` 需要当前密码重新验证，返回版本化 JSON：

- 包含账号、资料、普通偏好、安全问题文本、认证会话展示信息、学习状态、收藏、短期与长期 Agent 对话及其消息、同意事件和精简审计事件。
- Agent 对话导出仅包含用户可见标识、标题、置顶/到期/创建/更新时间和用户可见消息；不包含内部请求幂等标识、长期对话来源短期会话标识、Provider 原始载荷、系统提示或推理过程。
- 不包含密码哈希、密保答案哈希、访问/刷新令牌、刷新令牌哈希、Cookie 或完整审计元数据。
- 导出请求写入 `user_data_requests` 并记录审计事件。

## 注销阶段

1. 用户通过当前密码提交注销申请；同一用户只允许一个 pending/processing 申请。
2. 默认等待 7 天，期间用户可以取消。
3. 到期后由具有 `users:manage` 权限的受控命令执行软删除：账号状态改为 deleted、访问令牌版本递增、全部会话撤销。
4. 默认保留 30 天恢复期；受控恢复命令可恢复账号状态，但已撤销的认证会话不会恢复。短期和长期 Agent 对话在恢复期内保留。
5. 恢复期结束后，受控匿名化命令清除身份凭据、认证会话、短期与长期 Agent 对话、密保、角色和私有学习状态，并重置资料/偏好。
6. 匿名化保留不可识别的账号壳、数据请求和审计事实，避免破坏外键与合规记录；公开 Learning、Tools 和内容事实不受影响。

等待期和保留期分别由 `AI_NAV_ACCOUNT_DELETION_GRACE_DAYS` 与 `AI_NAV_ACCOUNT_DELETION_RETENTION_DAYS` 配置。物理删除不通过用户请求直接执行，需要独立的运维审批与备份检查。

## 恢复与匿名化边界

- pending 申请只能由所属用户取消，接口不接受客户端 `userId`。
- execute、restore、anonymize 只接受稳定 `request_uid`，目标用户从服务端请求记录解析。
- 管理命令必须通过后端 `users:manage` permission dependency。
- 匿名化会撤销当前同意、清理受管理头像文件和该用户的短期/长期 Agent 对话，并保留其他用户数据和公共领域事实。
