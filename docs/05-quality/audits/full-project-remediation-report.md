# AI 知识导航全项目审计整改报告

> 状态：七批本地整改及独立复验问题已关闭；外部生产签收阻塞  
> 整改日期：2026-07-25  
> 基准提交：`45238d4e1054ff5240bb924f78210cbb2bbd33d0`  
> 当前分支：`agent/sync-agent-foundation-cn`  
> 工作树范围：包含整改开始前已有的未提交开发成果与文档迁移；本轮未覆盖或回滚这些改动。  
> 当前发布判断：**NO-GO；本地整改候选通过，外部生产签收未验证。**  
> 独立复验：`docs/05-quality/audits/full-project-remediation-verification-report.md`

## 1. 状态总览

| 批次 | AUD ID | 状态 | 说明 |
| ---: | --- | --- | --- |
| 1 | AUD-SEC-001A / AUD-SEC-001B | 修复；发送服务外部阻塞 | 密保不再独立授权恢复，公开响应不可枚举；真实邮件/短信 Provider 未选择 |
| 2 | AUD-CFG-001 | 修复 | 生产配置和验证入口 fail-closed |
| 3 | AUD-SCA-001 | 修复 | 依赖升级、输入边界与有界拒绝服务回归 |
| 4 | AUD-WEB-002 / AUD-AUTH-002 | 修复 | Web 安全头和令牌边界 |
| 4 | AUD-API-002 | 修复并复验通过 | 84/84 JSON 操作使用字段级响应 DTO；额外字段过滤反例通过 |
| 5 | AUD-CI-002 / AUD-CI-003 | 修复 | CI 与质量门禁 |
| 6 | AUD-TEST-004 / AUD-CODE-003 / AUD-DB-004 / AUD-REP-003 | 修复 | 边界覆盖和工程问题 |
| 7 | AUD-OPS-002 | 外部阻塞 / 未验证（NO-GO） | 真实 Provider、生产网络、容量、恢复与回滚 |

## 2. 第 1 批：账户恢复与账号枚举

### 失败回归

整改前新增账户恢复专项测试，首次运行以缺少新的外部发送端领域边界失败：

```text
ModuleNotFoundError: app.users.authentication.recovery
```

这组回归随后用于驱动实现，不把旧“密保答案可成功重置”的正向测试继续当作安全行为。

### 修复

- 新增 `backend/app/users/authentication/recovery.py`，定义可替换发送端口、默认禁用发送端和仅供测试的内存发送端。
- 恢复凭据由密码学安全随机数生成；数据库仅保存 HMAC，绑定用户、`password_reset` 用途、恢复通道、过期时间和单次消费状态。
- `/api/v1/auth/password-reset/start` 对存在、缺失、未验证通道和发送端不可用统一返回 `200` 与同一公开结构。
- `/api/v1/auth/password-reset/confirm` 消费一次性凭据、更新密码、提升 token version 并撤销用户全部会话。
- 旧 `/password-reset/security/start|confirm` 保留为弃用别名；安全答案 verify 固定返回
  `SECURITY_RESET_DEPRECATED / 410`，不能再签发恢复权限。
- 前端改为“发送恢复说明 → 输入一次性恢复凭据”，不再呈现密保答案恢复表单。
- 审计只记录 `stage` 与 `sessionsRevoked` 白名单摘要，不记录 identifier、通道目标、凭据、答案或新密码。

### 验证

| 门禁 | 实际结果 |
| --- | ---: |
| 账户恢复专项 | 3/3 通过 |
| Users Python | 45/45 通过 |
| Auth/API Node | 10/10 通过 |

机器证据：`docs/06-evidence/users/password_recovery_remediation.json`。

### 兼容与剩余风险

- 已签发但尚未消费的旧密保型 reset token 因目标类型不再匹配而失效。
- 安全问题的配置与展示暂时保留，仅作为账号设置数据，不能用于密码恢复。
- 项目尚未选择、采购或授权真实邮件/短信发送服务。默认运行组合不会发送，也不会把凭据返回客户端；真实发送端接入和安全通知属于外部上线阻塞。

## 3. 第 2 批：生产配置 fail-closed

### 失败回归

新增危险组合测试后，旧校验函数因不接受数据库、上传目录与重置开关而失败：

```text
TypeError: validate_runtime_security() got an unexpected keyword argument 'database_path'
```

### 修复

- `AI_NAV_ENV=production` 明确拒绝 `RESET_DATABASE_ON_START=1`。
- 新增 `AI_NAV_UPLOAD_DIR`；生产数据库与上传目录必须位于应用源码树外。
- 生产 CORS 只允许无凭据、路径、查询和片段的显式 HTTPS origin。
- 校验 Refresh Cookie Secure/SameSite、可信代理全地址空间、账号删除宽限/保留期、
  单 Worker/进程内状态以及 Provider、成本和会话保留期组合。
- `.env.example` 补齐全部部署人员需要理解的非秘密配置；新增无真实值的
  `production.env.example`。
- `scripts/python-runtime.ps1` 为所有门禁进程设置 `AI_NAV_DISABLE_DOTENV=1`；
  验证不会读取真实 `.env`。
- 生产环境在配置导入/启动阶段执行 Provider 组合校验；开发环境仍保留无 Provider
  时的确定性降级。

### 验证

| 门禁 | 实际结果 |
| --- | ---: |
| 配置专项 | 3/3 通过 |
| Frontend Node | 26/26 通过 |
| Tools Python | 6/6 通过 |
| Learning Python / Node | 19/19、2/2 通过 |
| Users Python | 47/47 通过 |
| Agent Python / Node | 91/91、3/3 通过 |
| 数据库 | 20 个迁移；integrity `ok`；外键错误 0；checksum 一致 |

机器证据：`docs/06-evidence/platform/production_config_remediation.json`。

## 4. 第 3 批：依赖与输入处理

### 失败回归

- 截断 PNG 首次通过 Pillow `verify()` 时抛出未归一化的 `SyntaxError`，已纳入稳定
  `AVATAR_INVALID_IMAGE / 422` 错误边界。
- FastAPI 0.139 的惰性路由表示使原命令安全脚本把 35 条注册命令全部误判为陈旧；
  新增兼容的具体路由迭代入口后恢复 35/35 覆盖。

### 修复

- 升级并锁定 FastAPI 0.139.2、Starlette 1.3.1、python-multipart 0.0.32、
  Pillow 12.3.0；保存 Python 3.13/Windows 的运行依赖快照。
- 头像在 Pillow 选择解码器前检查 JPEG/PNG/GIF/WebP 文件签名，再校验声明 MIME、
  解码格式、完整性、源大小、像素、帧数、尺寸、输出大小和处理时间。
- 头像 multipart 在表单解析前要求并限制 `Content-Length`；应用仍在读取文件时执行
  第二层源文件字节限制。
- 增加 multipart header、preamble/epilogue、头像超大请求和 StaticFiles 多 Range
  有界回归。
- `pip-audit` 由 3 个受影响包、39 条含重复/别名记录，变为
  `No known vulnerabilities found`；审计证据按组件根因和实际调用路径归并。

### 验证

| 门禁 | 实际结果 |
| --- | ---: |
| `pip-audit -r backend/requirements.txt` | 0 个已知漏洞 |
| 输入安全专项 | 3/3 通过 |
| 头像专项 | 2/2 通过 |
| Users Python | 48/48 通过 |
| Agent Python / Node | 91/91、3/3 通过 |

机器证据：`docs/06-evidence/platform/dependency_input_remediation.json`。

## 5. 第 4 批：Web、令牌和响应契约

### 修复

- 所有响应统一增加 `nosniff`、不含 `unsafe-eval` 的 CSP、Referrer Policy、
  点击劫持防护和最小 Permissions Policy。只有生产模式且
  `AI_NAV_HTTPS_CONFIRMED=1` 时才发送 HSTS。
- Access Token 从 `localStorage` 迁移到 JavaScript 模块内存；模块加载会删除两个旧
  token key。页面刷新后通过 HttpOnly Refresh Cookie 单次恢复，不持久化 Access Token。
- 登录、注册和 refresh 的 JSON 响应不再暴露 Refresh Token；Refresh Token 只经
  HttpOnly Cookie 轮换。默认 Access Token 生命周期由 30 分钟缩短到 10 分钟。
- 保持写请求不做网络重试；只有明确 token 过期/无效的 401 才执行一次 refresh 后重放，
  业务 401 不重放。
- Auth、Platform、Tools、Users、Privacy、Assets、Agent 和运维指标均使用领域所有的
  字段级输出 schema。独立复验发现的 44 个宽泛 `JsonObject` 已归零；84/84 个 JSON
  操作全部具有字段级成功响应模型，并新增服务层额外内部字段在序列化前被过滤的反例。
- SSE 和三个 `204` 删除响应明确作为非 JSON 例外。

### 验证

| 门禁 | 实际结果 |
| --- | ---: |
| Web/Token Node | 14/14 通过 |
| 响应头与 OpenAPI 专项 | 5/5 通过 |
| Users Python | 48/48 通过 |
| Users 命令安全 | 35/35 通过 |
| Users 安全基线 | 28 pass / 0 known risk / 0 fail |

机器证据：`docs/06-evidence/platform/web_token_response_remediation.json`。

## 6. 第 5 批：CI 与质量门禁

- 工作流顶层权限固定为 `contents: read`；checkout、setup-python、setup-node 和
  upload-artifact 均固定到官方仓库当前 major tag 对应的完整提交 SHA，并保留版本注释。
- 保持 Windows、Python 3.12、Node 22 主门禁和 30 分钟超时。
- 新增固定版本 `coverage 7.15.2`、`pip-audit 2.10.1`、`ruff 0.16.0`，
  由 `scripts/verify-quality.ps1` 统一执行。
- 分支模式 169/169 测试通过，总覆盖率 84.1%，门槛设为 84%，禁止下降但不制造
  无关覆盖率噪声；依赖审计为 0。
- Ruff 核心规则准确复现 4 个既有命中。本批不使用忽略规则掩盖，按提示词顺序在第 6 批
  做最小行为保持修复后再将整套质量门禁标记为绿色。

机器证据：`docs/06-evidence/platform/ci_quality_remediation.json`。

## 7. 第 6 批：边界覆盖与工程问题

- 新增 5 个 ASGI/Windows 边界测试，覆盖未登录拒绝、注入用户所有权、跨用户缺失
  不可区分、隐私导出重新认证、删除/撤销、日志脱敏、Provider 故障时公共内容可用。
- 对 2 个未使用导入、1 个未使用变量和 1 个 lambda 赋值做最小修复；Ruff
  `E4/E7/E9/F` 当前 0 命中。
- `initialize_database()` 用显式 `closing` 关闭启动连接；Windows 实测返回后可立即
  重命名、打开校验并删除临时数据库，无 `gc.collect()`。
- `.gitignore` 显式排除日志、前端副本、覆盖率临时文件、SQLite/恢复临时文件、上传、
  IDE 与本地运行目录。
- 新增 allowlist 发布包脚本；后续整改复验选择 347 个文件、禁入产物 0 个，真实输出默认拒绝覆盖
  已存在归档。
- 完整质量门禁通过：176/176 Python，分支模式总覆盖率 85.9%，Ruff 0，
  `pip-audit` 0。

机器证据：`docs/06-evidence/platform/boundary_engineering_remediation.json` 和
`docs/06-evidence/platform/coverage.json`。

## 8. 第 7 批：外部生产签收

当前没有真实云环境、Provider/费用授权、合规签字、目标 C4G 实例或生产数据库变更窗口。
因此本批未读取或猜测任何密钥，未调用真实 Provider，未发起付费、容量或生产流量，也
未生成伪造成功证据。

已新增 `docs/04-operations/production-external-signoff-checklist.md`，逐项列出：

- 合规、云账户、网络、身份恢复通道、评测、性能、数据库、发布和运维责任人；
- 所需授权与输入；
- 受控执行命令或动作；
- 成功条件、停止/回滚条件和证据位置；
- 当前全部为“未验证”，最终决定保持 **NO-GO**。

本地整改完成不改变 AUD-OPS-002 的外部阻塞性质。

## 9. 最终全量复验与发布结论

### 本地门禁结果

| 门禁 | 2026-07-25 实际结果 |
| --- | ---: |
| 全量 Python | 176/176 通过 |
| 全量 Node | 34/34 通过 |
| Python 语法 | `compileall` 通过 |
| JavaScript 语法 | 36/36 文件通过 `node --check` |
| Ruff | `E4/E7/E9/F` 0 命中 |
| 依赖审计 | 0 个已知漏洞 |
| 分支模式总覆盖率 | 85.9%，门槛 84% |
| 发布 allowlist | 347 个文件，禁入产物 0 个 |
| 数据库 | 20 个迁移；integrity `ok`；外键错误 0；checksum 一致 |
| Frontend / Tools | 28/28、6/6 通过 |
| Learning Python / Node | 19/19、2/2 通过 |
| Users Python / 安全 / 命令 | 48/48、28 pass/0 risk/0 fail、35/35 通过 |
| Agent Python / Node | 91/91、3/3 通过 |
| 工作树格式 | `git diff --check` 通过 |

以上结果均来自禁用 dotenv 的本地门禁，不包含生产环境、真实恢复发送端、真实 Provider、
云网络或付费容量验证。独立复验的本地性能快照中，Learning p50 为 3.135 ms、p95 为
5.712 ms、最大值为 6.181 ms；Users 登录 p95 为 70.407 ms。这些数字仅用于本地
回归，不替代目标 C4G 与真实网络容量验收。

### 兼容性与迁移影响

- 旧密保恢复凭据不再可用；密保数据可保留展示，但不能授权密码重置。
- 前端加载时清除旧 localStorage token；Access Token 仅驻留内存，页面刷新依赖
  HttpOnly Refresh Cookie。Auth JSON 不再返回 Refresh Token。
- Access Token 默认生命周期由 30 分钟缩短为 10 分钟；已签发会话仍受 token version
  和会话撤销规则约束。
- 运行依赖升级并增加锁定快照；FastAPI 惰性路由通过统一迭代入口兼容现有安全与契约脚本。
- 本轮没有新增数据库迁移，迁移总数保持 20；数据库启动连接改为确定性关闭。
- 生产 HSTS 仅在 `AI_NAV_HTTPS_CONFIRMED=1` 时启用；发布包改用 allowlist，已存在输出
  默认拒绝覆盖。
- Starlette 测试客户端当前会提示未来迁移到 `httpx2` 的非阻断弃用警告；应用 Provider
  仍使用锁定的 `httpx`。应在后续独立兼容性批次评估，不影响本轮通过结果。

### 最终判断

- **本地整改候选：通过。** 所有可离线验证的问题已关闭并留存机器证据。
- **生产发布：NO-GO。** 真实恢复发送端、Provider 合规/受控调用、北京空间与上海出口、
  费用硬限制、C4G 容量、生产备份恢复、回滚、告警和值守仍未获得外部授权和签收。
- 只有 `docs/04-operations/production-external-signoff-checklist.md` 全部由责任人填写证据并
  签收后，才可重新评估 GO；不得用本地测试结果代替这些证据。
