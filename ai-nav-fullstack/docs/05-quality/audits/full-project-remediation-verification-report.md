# AI 知识导航全项目审计整改独立复验报告

> 状态：独立复验及后续本地整改完成；生产发布继续 NO-GO  
> 复验日期：2026-07-25  
> 基准提交：`45238d4e1054ff5240bb924f78210cbb2bbd33d0`  
> 当前分支：`agent/sync-agent-foundation-cn`  
> 权威性：本报告记录当前工作树的独立复验结果；发生冲突时，以实际代码、迁移和本次重跑结果为准。  
> 安全边界：全程设置 `AI_NAV_DISABLE_DOTENV=1`；未读取真实 `.env`，未调用真实 Provider，未发起付费、生产、容量或云网络流量。

## 1. 最终判断

- **本地整改候选：通过。** 账户恢复、生产配置、依赖与输入、Web 安全头、令牌存储、
  字段级响应契约、CI/质量门禁、HTTP 边界和工程问题的本地路径全部通过。独立复验发现的
  44 个宽泛响应模型已完成后续整改并通过正反例与全量门禁。
- **生产发布：NO-GO。** 真实恢复发送端、Provider 合规与受控调用、生产网络、费用、
  C4G 容量、生产备份恢复、回滚、告警和值守均未获得外部授权和签收。本地测试通过不改变
  该结论。

## 2. 复验范围与工作树保护

开始复验时记录到：

| 项目 | 实际值 |
| --- | --- |
| 分支 | `agent/sync-agent-foundation-cn` |
| HEAD | `45238d4e1054ff5240bb924f78210cbb2bbd33d0` |
| 工作树 | 已包含大量未提交实现、文档迁移和生成物；无法可靠区分每项改动的原始归属 |
| 处置 | 未 reset、checkout、clean、回滚或覆盖既有改动；只更正确认的文档/证据事实错误 |

复验按 `docs/00-index/remediation-file-index.md` 路由，完整对照了整改报告、复审报告、
原始审计、成果交接、文档地图、架构边界、整改提示词、外部签收清单，以及七批对应实现、
测试、脚本和 `docs/06-evidence/` 机器证据。

## 3. 七批独立结论

| 批次 | AUD ID | 独立结论 | 关键依据 |
| ---: | --- | --- | --- |
| 1 | AUD-SEC-001A / AUD-SEC-001B | 本地通过；真实发送端外部阻塞 | 恢复凭据摘要、用途/用户/通道/过期/单次消费绑定；枚举、篡改、重放、跨用户和会话撤销回归 |
| 2 | AUD-CFG-001 | 通过 | 生产危险组合 fail-closed；安全最小配置可加载；验证入口禁用 dotenv |
| 3 | AUD-SCA-001 | 通过 | 依赖锁定与审计、图片签名/解码/资源上限、multipart 与 Range 有界回归 |
| 4 | AUD-WEB-002 | 通过 | HTML、API、错误与静态资源安全头；CSP 无 `unsafe-eval`；HSTS 条件开启 |
| 4 | AUD-AUTH-002 | 通过 | Access Token 仅内存；Refresh Cookie 恢复；写请求和业务 401 不自动重放 |
| 4 | AUD-API-002 | **通过** | 44 个宽泛模型已替换；84/84 JSON 操作使用字段级响应 DTO，额外字段过滤反例通过 |
| 5 | AUD-CI-002 / AUD-CI-003 | 本地通过 | 最小权限、完整 SHA、Windows/Python 3.12/Node 22/超时、Ruff/SCA/覆盖率/发布校验 |
| 6 | AUD-TEST-004 | 通过 | 5 个 HTTP/ASGI 边界专项通过，含未登录、跨用户、隐私重认证、脱敏和 Provider 故障降级 |
| 6 | AUD-CODE-003 | 通过 | Ruff `E4/E7/E9/F` 0 命中，未新增忽略项 |
| 6 | AUD-DB-004 | 通过 | Windows 初始化后可立即重命名/打开/删除；20 迁移、checksum、FK、integrity 通过 |
| 6 | AUD-REP-003 | 通过 | allowlist `ValidateOnly` 选择 347 个文件、禁入产物 0；默认拒绝覆盖 |
| 7 | AUD-OPS-002 | **外部阻塞 / 未验证** | 外部签收清单 10 项均未签收，NO-GO 保持 |

## 4. 关键安全性质的正反例

### 4.1 账户恢复

- 公开 start 响应对存在和不存在账号保持相同状态与结构；默认发送端不可用时 fail-closed。
- 服务端只保存恢复凭据摘要；凭据绑定用户、用途、目标通道、过期时间和消费状态。
- 过期、篡改、重放、跨用户使用均失败；成功确认后更新 token version、撤销会话并在同一
  事务消费恢复凭据。
- 旧密保答案验证入口返回 `410`，前端不再把密保答案作为恢复授权。
- 专项账户恢复 3 项与生产配置 3 项均通过。
- 未验证真实邮件/短信到达率、发送时延和供应商隐私边界；这些继续属于外部签收。

### 4.2 生产配置

- 生产模式拒绝启动重置、默认/短密钥、危险 CORS/Cookie/可信代理、多 Worker 进程内
  状态、源码树内数据目录和不安全 Provider/费用/保留期组合。
- `.env.example` 与 `production.env.example` 只作为无密钥模板检查；复验未读取真实
  `.env`。

### 4.3 依赖与输入

- 当前锁定运行组合为 FastAPI 0.139.2、Starlette 1.3.1、
  python-multipart 0.0.32、Pillow 12.3.0；本地安装版本与锁定文件一致。
- `pip-audit -r backend/requirements.txt` 返回 `No known vulnerabilities found`。
- 头像处理在 Pillow 解码前检查文件签名与声明 MIME，随后校验实际格式，并限制请求字节、
  像素、尺寸、帧、处理时间和输出大小。
- 损坏/截断图片、像素炸弹、伪造 MIME、超大 multipart、异常 header/preamble/epilogue
  和 StaticFiles Range 的 7 个专项测试通过。

### 4.4 Web、令牌与输出契约

- 安全响应头专项验证覆盖 `/`、API、404 和静态资源；CSP 不含 `unsafe-eval`。
- 前端模块加载会清理旧 token key；Access Token 只驻留模块内存，刷新仅通过 HttpOnly
  Refresh Cookie；认证 JSON 不返回 Refresh Token。
- 13 个 Auth/API/Users Node 专项与 5 个响应头/输入/OpenAPI Python 专项通过。
- OpenAPI 当前有 88 个 HTTP 操作，其中 84 个 JSON 操作都有成功 schema；SSE 和三个
  `204` 响应是明确例外。
- 初次反证检查发现 44 个路由仍声明宽泛 `JsonObject`。后续整改已按 Platform、Tools、
  Users、Privacy、Assets、Agent 和运维指标的领域所有权补齐字段级 DTO，并移除
  `JsonObject` 别名。当前 84/84 个 JSON 操作均使用 Pydantic 字段级响应模型。
- 新增反例向导航服务结果嵌入未声明的 `internalSecret`，HTTP 响应仅保留声明字段且不含
  该值；同时静态遍历 84 个响应模型，确认不存在顶层 `dict`/`Any` 响应模型。

### 4.5 架构边界

- API 路由中跨领域 repository 直接导入为 0。
- 路由内 SQL 命中 2 行，均位于 Platform readiness 检查，只执行 `SELECT 1` 和迁移版本
  读取；未发现领域 SQL 或复杂业务规则复制。
- Provider 构造失败时公共 Learning 与导航仍可用的回归通过。
- Learning 保持用户无关；Users 继续拥有进度、活动、收藏、最近阅读、隐私、会话和用户
  资产；Agent 通过公开服务/适配器读取最小上下文。

## 5. 本次真实门禁结果

| 门禁 | 本次结果 |
| --- | ---: |
| `scripts/verify-quality.ps1` | 通过 |
| 全量 Python | 176/176 通过 |
| 分支模式覆盖率 | 85.9%，6262 statements、712 missed、1272 branches、297 partial；门槛 84% |
| 全量 Node | 34/34 通过（9 个测试文件） |
| Python `compileall` | 通过 |
| JavaScript `node --check` | 36/36 个 `.js`/`.mjs` 文件通过 |
| Ruff | `E4/E7/E9/F` 0 命中 |
| 依赖审计 | 0 个已知漏洞 |
| 发布 allowlist | 347 个文件，禁入产物 0，`ValidateOnly` |
| Frontend / Tools | 28/28、6/6 通过 |
| Learning Python / Node | 19/19、2/2 通过 |
| Users Python / 安全 / 命令 | 48/48、28 pass/0 risk/0 fail、35/35 通过 |
| Agent Python / Node | 91/91、3/3 通过 |
| 数据库 | 20 个迁移；integrity `ok`；外键错误 0；checksum 一致 |
| 证据 JSON | 29/29 可由标准 JSON 解析器解析 |
| 文档显式路径 | 关键入口 141/141 存在 |
| 工作树格式 | `git diff --check` 通过（仅有行尾转换警告） |

后续整改复跑的本地性能快照：Learning p50 3.223 ms、p95 5.705 ms、最大 6.017 ms；
Users 登录 p50 68.525 ms、p95 68.698 ms、最大 69.087 ms。性能数字仅用于同机回归，
不代表生产 C4G、真实网络或 Provider 容量。

## 6. 与整改报告的差异及处理

| 项目 | 整改报告/旧证据 | 本次复验 | 处理 |
| --- | ---: | ---: | --- |
| AUD-API-002 | 初次整改报告称已修复 | 初次复验为部分通过，后续整改后通过 | 44 个宽泛模型替换为领域字段级 DTO，并增加内部字段过滤反例 |
| 发布 allowlist | 343 | 347 | 独立报告及三个领域 schema 文件进入当前选择；同步报告与两份平台证据 |
| JS/MJS 语法文件 | 34 | 36 | 当前文件树实际枚举 36；同步报告与平台证据 |
| Learning 性能 | p50 2.990 / p95 5.529 / max 5.966 ms | p50 3.135 / p95 5.712 / max 6.181 ms | 使用本次重跑数字 |
| Users 登录 p95 | 77.765 ms | 70.407 ms | 使用本次重跑生成物 |
| 交接依赖/令牌/测试数 | 旧版本、localStorage token、30 分钟、25/47 | 当前版本、仅内存、10 分钟、28/48 | 更正交接文档 |

后续整改新增 `backend/app/platform/schemas.py`、`backend/app/tools/schemas.py` 和
`backend/app/users/response_schemas.py`，扩展 Users Assets 与 Agent schema，并将 44 个
路由切换到字段级响应模型。新增两项响应契约测试，同时把隐私删除边界测试的模拟返回值
校正为实际服务契约。没有修改数据库迁移、生产配置或外部签收状态。

## 7. 剩余风险与下一步

### 本地整改项

当前审计范围内没有仍然开放的本地整改项。字段级 DTO、额外字段过滤反例、OpenAPI/Users
契约冻结、Foundation、Agent 和统一质量门禁均已完成。

### 外部阻塞

严格按 `docs/04-operations/production-external-signoff-checklist.md` 执行。当前 10 项均为
未验证；不得在缺少真实环境、授权、合规签字和费用许可时执行或伪造结果。

## 8. 权威入口

- 文件路由：`docs/00-index/remediation-file-index.md`
- 本独立复验：`docs/05-quality/audits/full-project-remediation-verification-report.md`
- 整改实施记录：`docs/05-quality/audits/full-project-remediation-report.md`
- 原复审与首审：`docs/05-quality/audits/full-project-reaudit-report.md`、
  `docs/05-quality/audits/full-project-audit-report.md`
- 架构边界：`docs/02-architecture/modular-monolith-guidelines.md`
- 外部签收：`docs/04-operations/production-external-signoff-checklist.md`
- 机器证据：`docs/06-evidence/`
