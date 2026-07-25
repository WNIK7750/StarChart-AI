# AI 知识导航全项目审计报告

> 审计日期：2026-07-25  
> 基准提交：`45238d4e1054ff5240bb924f78210cbb2bbd33d0`  
> 当前分支：`agent/sync-agent-foundation-cn`  
> 范围：当前工作树，包括未提交开发成果  
> 结论：**离线开发门禁通过；生产上线 NO-GO**

> 复审更新：本报告中的既有问题已于 2026-07-25 逐项回测。当前最终判定以
> `docs/05-quality/audits/full-project-remediation-verification-report.md` 为准；
> 上一轮加权复核见 `docs/05-quality/audits/full-project-reaudit-report.md`。

## 1. 执行摘要

项目的模块化单体方向、数据库迁移、用户隔离、Agent 确定性回退、离线测试和备份恢复基础整体可靠。Foundation 与 Agent 两套门禁均通过，未发现 Agent 越过 Learning/Tools/Users 公共边界直接访问其 repository，也未在受检代码中发现真实密钥。

但是，“开发完成、只剩部署操作”这一旧结论不能直接等同于生产可发布。本次审计确认 3 组 P1：

1. 密码重置允许仅凭安全问题完成账户恢复；
2. 三个运行依赖包含已知漏洞；
3. 生产配置模板缺少关键项，且危险的数据库重置开关没有在生产模式中 fail-closed。

在这些问题关闭前，不应开放真实用户注册、头像上传或生产 Provider 流量。

## 2. 审计快照

| 项目 | 结果 |
| --- | --- |
| Foundation 门禁 | 通过；Frontend 25、Tools 6、Learning 19 Python + 2 Node、Users 43 |
| Agent 门禁 | 通过；91 Python + 3 Node/SSE |
| 数据库 | 20 个迁移；完整性、外键、checksum、备份/恢复演练通过 |
| OpenAPI | 49 条路径、86 个 HTTP 操作 |
| 响应模型 | 29/86 操作显式声明；57/86 未声明 |
| 依赖审计 | 3 个包命中 39 条公告记录（含同一根因的重复/别名记录） |
| 核心静态检查 | Ruff `E4/E7/E9/F` 发现 4 项 |
| 密钥模式扫描 | 仅命中测试中的伪造样例；未发现真实密钥证据 |
| 代码体量 | 约 240 个受检源码/脚本文件，约 37,696 行 |

## 3. P1：上线前必须关闭

### AUD-SEC-001 安全问题是独立密码恢复因子

**证据**

- `backend/app/api/v1/routers/auth.py` 提供 start、verify、confirm 三段式安全问题重置接口；
- `backend/app/users/authentication/service.py` 在答案验证后签发 reset token；
- `tests/test_users_services.py` 证明只需正确答案即可设置新密码。

**风险**

攻击者若从社交信息、撞库数据或有限答案空间中猜中答案，可绕过原密码接管账户。答案已哈希、接口有限流和挑战令牌，这些措施降低数据库泄露与暴力枚举风险，但不能把可猜测的知识问答变成可靠认证器。

NIST 明确说明知识型认证（安全问题）不再是可接受认证器，且不应作为自助密码重置方式；OWASP 也要求安全问题不得成为唯一重置机制。[NIST FAQ B07/B15](https://pages.nist.gov/800-63-FAQ/?pubDate=20250428)、[OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)

**整改**

- 用一次性、短时、单用途的邮箱链接或验证码替代；
- 令牌使用加密安全随机数、服务端仅存哈希、绑定用户与用途、使用后作废；
- 返回统一文案与近似耗时，避免账号枚举；
- 重置后撤销全部会话并发送安全通知；
- 安全问题仅可保留为迁移期附加验证，不能独立授权重置。

**复验**

新增“不拥有邮箱/外部验证通道时无法重置”“令牌单次使用/过期/重放失败”“重置后全部会话失效”和账号枚举时序测试。

### AUD-SCA-001 运行依赖存在已知漏洞（2026-07-25 已整改）

**证据**

2026-07-25 使用 `pip-audit` 审计 `backend/requirements.txt`：

| 包 | 当前版本 | 公告结果 | 最低完整修复目标 |
| --- | ---: | --- | ---: |
| `python-multipart` | 0.0.20 | 多条 2026 PYSEC 公告 | 0.0.31 或更高 |
| `Pillow` | 10.4.0 | 多条 2026 PYSEC 公告 | 12.3.0 或更高 |
| `starlette`（FastAPI 间接依赖） | 0.46.2 | 多条 2026 PYSEC 公告 | 需升级 FastAPI/Starlette 到覆盖全部适用修复的兼容组合 |

当前项目正好使用 multipart 头像上传、Pillow 解码和 Starlette/FastAPI 请求处理，因此不能将结果标记为“不适用”。

**整改**

- 在独立分支升级 FastAPI、python-multipart、Pillow，并生成锁定的完整依赖快照；
- 复跑头像伪造、像素炸弹、超限上传、API/OpenAPI、Foundation 和 Agent 全门禁；
- 将 `pip-audit` 加入 CI，阻止新增适用漏洞；
- 对重复公告按 CVE/PYSEC 根因去重后归档风险接受或修复证据。

**复验**

升级到 FastAPI 0.139.2、Starlette 1.3.1、python-multipart 0.0.32 和 Pillow
12.3.0 后，`pip-audit -r backend/requirements.txt` 返回无已知漏洞。头像签名、格式、
帧数、时间和请求体边界，以及 multipart 与 StaticFiles Range 有界回归均已加入；
去重证据见 `docs/06-evidence/platform/dependency_input_remediation.json`。

`pip-audit` 无适用已知漏洞，且全量门禁在 Python 3.12 CI 与项目本机环境均通过。

### AUD-CFG-001 生产配置契约不完整且危险开关未 fail-closed

**证据**

- `backend/app/core/config.py` 读取约 58 个配置名，`.env.example` 只列出 30 个；
- 模板缺少 `AI_NAV_SECRET_KEY`、`AI_NAV_DATABASE_PATH`、`AI_NAV_CORS_ALLOW_ORIGINS`、`AI_NAV_TRUSTED_PROXY_CIDRS`、`AI_NAV_REFRESH_COOKIE_SECURE` 等生产关键项；
- `RESET_DATABASE_ON_START=1` 会在数据库存在时触发重建，但生产安全校验没有拒绝该组合；
- 默认数据库仍位于源码目录内，生产必须显式覆盖。

**风险**

部署人员只按模板配置时，无法得到完整且可审计的生产契约；错误启用重置开关可能造成生产数据破坏。

**整改**

- 补全无密钥值的生产配置模板或独立 `production.env.example`；
- 在 `AI_NAV_ENV=production` 时强制拒绝 `RESET_DATABASE_ON_START=1`；
- 对数据库路径、上传目录、Cookie、CORS、代理、保留期和成本阈值增加启动期校验；
- 在发布演练中验证“缺少关键配置即启动失败”。

**复验**

从空环境只按模板配置可通过启动前检查；危险组合测试全部 fail-closed；数据库和上传目录均位于持久化目录。

## 4. P2：应纳入上线评审

| ID | 发现 | 影响与建议 |
| --- | --- | --- |
| AUD-WEB-002 | 已整改：HTML/API/错误/静态资源统一安全响应头 | HSTS 只在生产 HTTPS 显式确认后启用 |
| AUD-AUTH-002 | 已整改：Access Token 仅驻留内存 | 页面刷新通过 HttpOnly Cookie 恢复，JSON 不返回 Refresh Token |
| AUD-API-002 | 后续整改并独立复验通过：84/84 JSON 操作使用字段级响应模型 | 44 个宽泛模型归零；额外内部字段过滤反例通过；SSE 与三个 204 空响应为书面例外 |
| AUD-CI-002 | 已整改：Action 固定完整 SHA，顶层 `contents: read` | 保留 major 版本注释便于受控升级 |
| AUD-CI-003 | 已实施：pip-audit、Ruff 与 84% 分支覆盖率门禁 | 169 个本地测试的当前覆盖率为 84.1% |
| AUD-OPS-002 | 真实 Provider 合规、上海到北京链路、2C4G 容量和生产恢复仍无本地证据 | 继续作为人工上线门禁，不得用离线测试替代 |
| AUD-DOC-002 | 旧交接文档把“离线开发完成”表述成接近生产完成 | 已增加本次审计覆盖声明；后续状态以本报告为准 |

GitHub 建议对工作流声明最小权限并将 Action 固定到完整提交 SHA，以降低供应链攻击风险。[GitHub Actions 安全加固](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats)

## 5. P3：工程质量债

| ID | 发现 | 建议 |
| --- | --- | --- |
| AUD-CODE-003 | 已整改：4 个核心 Ruff 命中已做最小修复 | `E4/E7/E9/F` 门禁当前通过 |
| AUD-CODE-004 | `index.html`、`settings.js`、`agent/sessions.py` 等文件较大 | 只在有真实变更压力时按职责拆分，避免为指标而拆分 |
| AUD-TEST-003 | 当前没有代码覆盖率数字 | 先生成只读基线，关注认证、隐私、迁移、Provider 和错误分支，不追求虚高百分比 |
| AUD-REP-003 | 已整改：ignore 与 allowlist 发布脚本均显式排除本地产物 | 后续整改复验选择 347 个文件、禁入 0 |

## 6. 已确认的正向控制

- Router 中没有领域业务 SQL；健康检查的数据库探针属于平台例外。
- Agent 未直接导入 Learning/Tools/Users repository。
- Learning 保持用户无关，Users 拥有学习进度、资产、隐私与审计。
- 生产默认密钥、通配 CORS、不安全 Refresh Cookie 和多 Worker/进程内状态组合会启动失败。
- Refresh Token 服务端仅存哈希并轮换；重放会撤销 token family。
- 用户隔离、RBAC、幂等、并发版本、审计字段白名单和删除生命周期有自动化测试。
- Provider 默认关闭，host allowlist、输入/证据/输出上限、超时、成本和并发有门禁。
- Provider 不可用时，公共 Learning/Tools/Users 与确定性 Agent 能力仍可用。
- 20 个迁移具备 checksum，旧库升级、新库初始化、外键、完整性和备份恢复演练通过。
- 外链协议、opener 隔离、共享错误转义、响应式和减少动画有前端契约测试。

## 7. 整改优先顺序

```text
第 1 批：账户恢复替换 + 危险配置 fail-closed
第 2 批：依赖升级 + pip-audit CI
第 3 批：安全响应头 + Access Token 风险降低
第 4 批：响应模型、CI 最小权限、静态检查与覆盖率基线
第 5 批：真实 Provider、容量、网络、备份和回滚签收
```

每一批必须独立提交、独立复验；不要把依赖大升级、认证流程重构和文档搬迁混在同一个不可审阅提交中。

## 8. 最终判定

| 维度 | 判定 |
| --- | --- |
| 离线功能开发 | 通过 |
| 架构边界 | 通过，存在少量可维护性债 |
| 数据完整性与恢复 | 本地通过 |
| 安全与供应链 | 不通过；3 组 P1 |
| 生产容量与外部合规 | 未验证 |
| 生产发布 | **NO-GO** |

本报告替代此前文档中任何“只需填写生产参数即可上线”的宽泛表述。关闭全部 P1、复跑门禁并完成外部签收后，方可重新进行生产就绪评审。
