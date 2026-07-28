# Users 审计事件目录

## 原则

- 审计只记录谁在何时对哪个资源执行了什么命令，以及经过白名单筛选的结果摘要。
- 不记录密码、密保答案、访问/刷新令牌、Cookie、Authorization、原始头像内容或资料字段值。
- `actor_user_id` 表示执行者，`target_user_id` 表示受影响用户；用户自助命令二者相同。
- 账号、资料、偏好等一对一资源使用稳定 `user_uid`；单个会话使用 `session_uid`。
- IP 与 User-Agent 来自服务端请求上下文，分别限制为 64 和 512 字符。

## 事件

| 事件 | 资源类型 | 资源标识 | 允许元数据 |
| --- | --- | --- | --- |
| `users.auth.registered` | `account` | `user_uid` | `sessionIssued` |
| `users.auth.login_succeeded` | `session` | `user_uid` | `sessionIssued` |
| `users.auth.password_reset_started` | `password_reset` | `user_uid` | `stage`（仅记录外部投递端已接受请求） |
| `users.auth.password_reset_verified` | `password_reset` | `user_uid` | `stage`（历史事件；密保验证入口已弃用，不再新增） |
| `users.auth.password_reset_completed` | `password_reset` | `user_uid` | `stage`, `sessionsRevoked` |
| `users.auth.session_refreshed` | `session` | `user_uid` | `rotation` |
| `users.auth.session_logged_out` | `session` | `user_uid` | `scope` |
| `users.account.updated` | `account` | `user_uid` | `changedFields` |
| `users.security.password_updated` | `security` | `user_uid` | `sessionsRevoked` |
| `users.security.questions_replaced` | `security_questions` | `user_uid` | `questionCount` |
| `users.profile.updated` | `profile` | `user_uid` | `changedFields` |
| `users.profile.avatar_updated` | `avatar` | `user_uid` | `format`, `storedBytes`, `oldAvatarRemoved` |
| `users.preferences.updated` | `preferences` | `user_uid` | `changedFields` |
| `users.session.revoked` | `session` | `session_uid` | `scope` |
| `users.sessions.others_revoked` | `session` | `user_uid` | `scope`, `revokedCount` |
| `users.privacy.consent_updated` | `privacy_consent` | 同意类型 | `consentType`, `policyVersion`, `status` |
| `users.privacy.data_exported` | `data_export` | `request_uid` | `formatVersion` |
| `users.privacy.deletion_requested` | `deletion_request` | `request_uid` | `reasonCode`, `scheduledFor` |
| `users.privacy.deletion_cancelled` | `deletion_request` | `request_uid` | 无 |
| `users.privacy.deletion_executed` | `deletion_request` | `request_uid` | `retentionUntil` |
| `users.privacy.deletion_restored` | `deletion_request` | `request_uid` | 无 |
| `users.privacy.deletion_anonymized` | `deletion_request` | `request_uid` | 无 |
| `users.assets.workflow_created` | `saved_workflow` | `workflow_uid` | `sourceType`, `stepCount` |
| `users.assets.workflow_updated` | `saved_workflow` | `workflow_uid` | `changedFields`, `version` |
| `users.assets.workflow_archived` | `saved_workflow` | `workflow_uid` | `version` |
| `users.assets.workflow_restored` | `saved_workflow` | `workflow_uid` | `version` |

事件必须先注册到 `backend/app/users/audit/events.py`。未知事件拒绝写入，额外元数据会被移除；敏感键即使出现在允许列表中也会再次被脱敏策略拦截。

密码恢复审计不记录 identifier、外部通道目标、一次性凭据、密保答案或新密码。
