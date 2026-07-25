# Users 认证限流与代理信任契约

## 限流存储

认证限流由 SQLite `user_auth_rate_limits` 统一保存，使用固定窗口和原子 upsert。主体值先通过服务端 HMAC 转为 `subject_hash`，数据库不保存原始用户名、邮箱、IP、challenge UID 或 reset token。

过期窗口在后续消费时清理。超过限制返回 `AUTH_RATE_LIMITED / 429` 和 `Retry-After`，不会继续调用认证业务服务。

| 操作 | 维度与窗口 |
| --- | --- |
| 用户名探测 | IP：30 次/60 秒 |
| 注册 | IP：5 次/300 秒 |
| 登录 | IP：20 次/60 秒；identifier：10 次/300 秒 |
| 重置开始 | IP：10 次/300 秒；identifier：5 次/300 秒 |
| 旧密保验证 | 已弃用并固定返回 `SECURITY_RESET_DEPRECATED / 410`；兼容入口仍保留限流 |
| 重置确认 | IP：10 次/300 秒；token：5 次/300 秒 |
| Token 刷新 | IP：30 次/60 秒 |

登录对存在、缺失、锁定和密码错误账号继续返回相同的 `INVALID_CREDENTIALS / 401`，避免通过响应差异判断账号状态。注册冲突也不区分用户名与邮箱。

密码恢复开始接口对存在账号、缺失账号、没有已验证恢复通道的账号和发送端不可用
统一返回 `200`、`status=accepted` 及同一公开文案。identifier 维度仍在服务端
HMAC 后限流。恢复凭据只通过可替换的外部发送端口交付，服务端仅保存 HMAC；
默认发送端关闭并 fail-closed，不会把凭据写入响应、日志或审计。

## 可信代理

默认不信任 `X-Forwarded-For`。只有请求的直连 peer IP 命中 `AI_NAV_TRUSTED_PROXY_CIDRS` 时，服务才从右向左解析代理链并选择第一个非可信地址；格式无效时回退到直连 IP。

```powershell
$env:AI_NAV_TRUSTED_PROXY_CIDRS="10.0.0.0/8,192.168.0.0/16"
```

该配置必须填写实际反向代理网段，不能填写所有公网范围。应用与代理之间应有网络访问控制，否则攻击者仍可能绕过代理直接连接应用。

## 前端刷新

统一 API client 在受保护请求收到 401 时，通过 HttpOnly refresh Cookie 调用一次 `/auth/refresh` 并重放原请求。并发 401 共享同一个 promise，避免 refresh token 被并发旋转后触发 replay 防护。登录、注册、刷新、退出、用户名探测和密码重置接口不会递归刷新。
