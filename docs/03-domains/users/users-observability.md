# Users 可观测性契约

## 访问日志

`/api/v1/auth/*`、`/api/v1/users/*` 和 Agent 工作流保存命令统一记录：

- `requestId`：仅接受 1 至 128 位字母、数字、点、下划线和连字符；其他输入替换为服务端随机值。
- `operation`：优先使用 FastAPI 路由模板，注册、登录、刷新、改密和会话撤销使用稳定操作名。
- `status`、`latencyMs`、`errorCode`。

日志不读取请求体、查询值、用户名、邮箱、IP、User-Agent、Authorization、Cookie、密码、答案或令牌。响应返回 `X-Request-Id` 和 `Server-Timing: users;dur=...`。

## 指标与告警

管理员接口：`GET /api/v1/users/operations/metrics`，需要 `users:manage`。普通用户返回 403。

指标按 `operation + outcome + errorCode` 聚合，不使用用户标识作为 label。当前进程维护累计 counter，并在 5 分钟滚动窗口内计算：

| 告警 | 条件 |
| --- | --- |
| `AUTH_LOGIN_FAILURE_SPIKE` | 登录错误达到 5 次 |
| `AUTH_ACCOUNT_LOCKED` | 出现账号锁定响应 |
| `AUTH_REFRESH_FAILURE_SPIKE` | 刷新错误达到 3 次 |
| `PASSWORD_UPDATE_FAILURE_SPIKE` | 改密错误达到 3 次 |
| `SESSION_REVOKE_FAILURE_SPIKE` | 会话撤销错误达到 3 次 |

当前 registry 是单进程运行时实现，适合本地部署和接口契约验证。多 worker/多实例生产环境应将同样的低基数指标发送到集中式监控系统，并在该系统复用以上窗口和阈值；不得增加用户名、邮箱、IP 或 token label。
