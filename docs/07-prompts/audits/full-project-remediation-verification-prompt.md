# AI 知识导航全项目审计整改独立复验提示词

> 用途：粘贴到原审计对话或新的 Codex 对话中，对 2026-07-25 七批整改做独立复验。  
> 适用工作区：`<PROJECT_ROOT>`
> 文件路由入口：`docs/00-index/remediation-file-index.md`  
> 待验证声明：`docs/05-quality/audits/full-project-remediation-report.md`  
> 状态：可直接执行；目标是验证实际效果，不是复述整改报告。

---

请进入工作区：

```text
<PROJECT_ROOT>
```

完整阅读并严格执行本提示词。首先使用：

```text
docs/00-index/remediation-file-index.md
```

作为文件路由、问题定位和进度同步入口，然后按以下顺序阅读：

1. `docs/05-quality/audits/full-project-remediation-report.md`
2. `docs/05-quality/audits/full-project-reaudit-report.md`
3. `docs/05-quality/audits/full-project-audit-report.md`
4. `docs/01-overview/fullstack-development-results-handoff.md`
5. `docs/00-index/documentation-map.md`
6. `docs/02-architecture/modular-monolith-guidelines.md`
7. `docs/07-prompts/audits/full-project-remediation-prompt.md`
8. `docs/04-operations/production-external-signoff-checklist.md`

不要直接接受整改报告中的“已修复”或测试数字。必须按照文件索引逐批找到实际实现、
测试、脚本和机器证据，从当前工作树重新验证。请直接开展复验，不要只输出复验计划。

## 一、复验目标

独立判断七批整改是否真实关闭了对应本地问题，并回答：

- 报告中的每个 AUD ID 是否有对应实现、攻击/失败路径回归和修复后证据；
- 测试是否验证安全性质，而不是只验证成功路径或内部实现细节；
- 配置、代码、测试、CI、运行手册、README、OpenAPI 和证据 JSON 是否一致；
- Learning、Users、Agent、Tools、Platform 的所有权边界是否保持；
- 当前结果是否只能证明本地整改候选，生产发布是否仍应保持 NO-GO；
- 是否存在遗漏、误报、证据过期、数字不一致或由整改引入的新回归。

复验完成标准不是“验证脚本退出码为 0”，而是代码检查、针对性反证、全量门禁和文档
交叉核对同时成立。

## 二、工作区与安全保护

开始前先记录：

```powershell
git status --short
git diff --stat
git branch --show-current
git rev-parse HEAD
```

必须遵守：

- 不执行 `git reset --hard`、`git checkout --`、`git clean` 或覆盖现有改动的操作；
- 不删除、回滚或格式化与复验无关的用户改动；
- 不读取、打印、复制、移动或修改真实 `.env`；
- 所有 Python 验证必须通过现有安全入口禁用 dotenv，或显式设置
  `AI_NAV_DISABLE_DOTENV=1`；
- 不记录真实密钥、用户数据、恢复凭据、Provider 请求正文或响应正文；
- 不调用真实 Provider，不发起付费、生产、容量或云网络流量；
- 不伪造生产环境、恢复发送端、合规、容量、备份恢复或回滚成功证据；
- 不擅自提交、推送或创建 PR；
- 先只读复验。只有发现可以从当前代码和测试确认的问题时，才做最小修复，并同步测试、
  文件索引、复验报告和受影响文档；
- 如果现有工作区改动与整改改动无法可靠区分，要在报告中明确范围，不得猜测归属。

## 三、必须保持的架构与安全不变量

复验时把以下内容作为硬约束：

- Learning 只拥有用户无关的公共学习内容；
- Users 拥有进度、活动、收藏、最近阅读、匿名导入、隐私、会话和用户资产；
- Agent 通过公开服务或薄适配器访问 Learning、Tools、Users，不直接访问其他领域 repository；
- Router 保持薄层，不复制领域 SQL 或复杂业务规则；
- Provider 故障不能拖垮公共 Learning、Tools、导航或确定性功能；
- Agent 只能接收最小化、经过敏感信息过滤的用户上下文；
- 未登录拒绝、跨用户不可区分、导出再认证、删除/撤销、幂等和审计白名单继续成立；
- 当前模块化单体、SQLite、单 Worker 是明确选择；不要为了复验引入微服务、Redis、
  向量库、多 Agent 或复杂状态图。

## 四、按七批逐项复验

每一批都按以下顺序推进：

```text
读取索引列出的实现和文档
  -> 对照原审计攻击/失败路径
  -> 检查测试是否真正覆盖该路径
  -> 独立运行专项测试
  -> 检查机器证据是否与本次结果一致
  -> 记录通过、部分通过、失败或外部阻塞
  -> 必要时最小修复并重新验证
```

### 第 1 批：账户恢复与账号枚举

复验 `AUD-SEC-001A`、`AUD-SEC-001B`：

- 密保答案不能单独签发密码重置权限；
- start 对存在、不存在、未验证通道和发送端不可用的账号保持相同公开状态与结构；
- 恢复凭据使用安全随机数，服务端只保存不可逆摘要，并绑定用户、用途、通道、过期时间
  和单次消费；
- 过期、重放、篡改、跨用户使用全部失败；
- 成功重置后撤销全部会话；
- 默认发送端 fail-closed，测试 Fake sender 不会进入生产装配；
- 日志、审计、错误和证据不含 identifier、目标地址、原始凭据、密保答案或新密码；
- 前端不再提供密保答案恢复流程；
- 真实邮件/短信发送服务仍应标为外部阻塞。

### 第 2 批：生产配置 fail-closed

复验 `AUD-CFG-001`：

- `AI_NAV_ENV=production` 拒绝数据库启动重置；
- 默认或短密钥、非 HTTPS/通配 CORS、不安全 Cookie、危险可信代理、多 Worker +
  进程内状态、源码树内数据库/上传路径以及危险 Provider/费用/保留期组合启动失败；
- 安全最小生产配置可以加载；
- `.env.example` 与 `production.env.example` 不含真实秘密且与代码字段一致；
- 所有验证脚本确实禁用 dotenv，不通过移动或读取真实 `.env` 绕过。

### 第 3 批：依赖与输入处理

复验 `AUD-SCA-001`：

- `backend/requirements.txt`、`backend/requirements-lock.txt` 与实际运行版本相符；
- 重新执行依赖审计，按当前输出记录结果，不沿用旧数字；
- 头像先检查签名并校验 MIME/解码格式，限制请求字节、像素、尺寸、帧数、处理时间和
  输出大小；
- 损坏、截断、像素炸弹、伪造 Content-Type 和超大 multipart 稳定失败；
- multipart header、preamble/epilogue 与 StaticFiles Range 路径有有界回归；
- 依赖升级没有破坏 OpenAPI、静态文件、Users、Foundation 或 Agent。

### 第 4 批：Web、令牌和响应契约

复验 `AUD-WEB-002`、`AUD-AUTH-002`、`AUD-API-002`：

- `/`、API、错误响应和静态资源均有安全响应头；
- CSP 不含 `unsafe-eval`，HSTS 只在生产 HTTPS 明确确认时启用；
- Access Token 只驻留内存，旧 localStorage token 会清理；
- 页面刷新仅经 HttpOnly Refresh Cookie 恢复；
- 登录、注册和 refresh JSON 不返回 Refresh Token；
- 写请求不会因普通网络失败或业务 401 自动重放；
- refresh token family 重放撤销仍成立；
- 所有 JSON 业务操作具有成功响应 schema；SSE、文件和 204 例外有明确说明；
- OpenAPI 与前端 DTO 没有非预期漂移。

### 第 5 批：CI 与质量门禁

复验 `AUD-CI-002`、`AUD-CI-003`：

- 工作流顶层权限为 `contents: read`；
- 第三方 Actions 固定完整 SHA，并保留可读版本注释；
- Windows、Python 3.12、Node 22 和超时约束仍存在；
- Ruff、依赖审计、发布包校验和分支覆盖率进入统一门禁；
- 覆盖率 fail-under 为 84%，实际结果不得低于门槛；
- 证据只能声明本地门禁结果，不能伪称托管 GitHub Actions 已运行。

### 第 6 批：边界覆盖与工程问题

复验 `AUD-TEST-004`、`AUD-CODE-003`、`AUD-DB-004`、`AUD-REP-003`：

- HTTP/ASGI 测试覆盖身份注入、未登录、跨用户不可区分、稳定错误码、响应脱敏、
  隐私导出/删除/撤销、重新认证、request id 和日志白名单；
- Provider 构造或调用故障时，公共 Learning 与导航保持可用；
- Ruff `E4/E7/E9/F` 为 0，且不是通过新增忽略掩盖；
- Windows 上数据库初始化返回后可立即重命名、打开并删除临时数据库，不依赖
  `gc.collect()`；
- `.gitignore` 与 allowlist 发布脚本排除日志、前端副本、覆盖率临时文件、SQLite
  sidecar/恢复临时文件、上传和 IDE/本地运行产物；
- 发布包验证只做 `ValidateOnly`，不得覆盖已有归档。

### 第 7 批：外部生产签收

复验 `AUD-OPS-002`：

- 阅读 `docs/04-operations/production-external-signoff-checklist.md`；
- 检查责任人、所需输入、操作、成功条件、停止/回滚条件和证据位置是否完整；
- 在没有真实环境、明确授权、合规签字和费用许可时，不执行任何外部动作；
- 所有未签收项继续标记为“外部阻塞/未验证”；
- 本地测试通过不能把生产结论从 NO-GO 改成 GO。

## 五、必须重新运行的本地验证

优先使用仓库脚本，不手工拼出绕过门禁的替代命令：

```powershell
.\scripts\verify-quality.ps1
.\scripts\verify-foundation.ps1
.\scripts\verify-agent.ps1
```

此外必须确认：

- 全量 `tests/test_*.py`；
- 全量 `tests/test_*.mjs`；
- Python `compileall`；
- 所有 `.js`、`.mjs` 的 `node --check`；
- Ruff `E4/E7/E9/F`；
- `pip-audit -r backend/requirements.txt`；
- 分支覆盖率与 84% 门槛；
- 新库初始化、20 个迁移、checksum、外键和 integrity；
- 恢复不可枚举、一次性凭据、会话撤销；
- Provider 敏感输入阻断、用户隔离和公共内容降级；
- 发布 allowlist 的 `ValidateOnly`；
- OpenAPI/Users/Agent 生成产物一致性；
- `git diff --check`；
- 文件索引、整改报告、README、交接文档和证据 JSON 中的显式路径真实存在；
- 所有证据 JSON 可以解析，且数字与本次运行结果一致。

测试数字必须使用本次实际结果。如果与整改报告不同，先查明是代码变化、环境差异、
生成物过期还是报告错误，再同步修正；不能为了匹配旧报告而修改测试结果。

## 六、问题处理与证据规则

发现问题时按以下类别记录：

1. **验证通过**：代码、针对性回归、全量门禁和文档一致；
2. **部分通过**：主要攻击路径关闭，但仍有本地可修复缺口；
3. **验证失败**：攻击路径仍可达、门禁失败或证据声明不成立；
4. **工作区原有失败**：有基线证据证明不由本轮整改造成；
5. **环境缺失**：本地工具或兼容环境确实缺失；
6. **外部阻塞**：需要生产凭据、云资源、合规或付费授权。

对于本地确认的问题：

- 先增加或修正能够失败的回归；
- 做最小范围实现修复；
- 重跑专项、受影响模块和全量门禁；
- 同步文件索引、复验报告、机器证据和受影响文档；
- 不覆盖历史审计或整改报告中的历史证据，只补充复验结论或更正明确错误。

不得仅根据代码阅读把问题标为通过，也不得仅根据一个总脚本通过推断所有安全性质成立。

## 七、复验交付与同步

新增独立复验报告：

```text
docs/05-quality/audits/full-project-remediation-verification-report.md
```

报告至少包括：

- 复验日期、HEAD、分支和开始时工作树范围；
- 七批及每个 AUD ID 的独立结论；
- 阅读过的实现、测试和证据入口；
- 关键安全性质的正反例验证；
- 本次实际测试数、覆盖率、Ruff、依赖审计、数据库和语法结果；
- 整改报告数字与本次结果的差异及原因；
- 发现并修复的问题，或明确说明没有额外修改；
- 仍未关闭的本地风险与外部阻塞；
- 本地整改候选和生产发布两个分开的最终判断。

同步更新：

- `docs/00-index/remediation-file-index.md`：增加复验报告入口和最终状态；
- `docs/00-index/documentation-map.md`：增加复验提示词与报告入口；
- `docs/05-quality/audits/full-project-remediation-report.md`：只在发现事实错误或需要引用
  独立复验结论时更新；
- `README.md`、交接文档、运行手册和机器证据：仅在复验发现不一致时更新。

## 八、沟通与最终输出

- 使用任务计划逐批跟踪，但不要停在计划阶段；
- 每完成 1～2 批，简短汇报“已检查范围、实际结果、发现的问题、下一步”；
- 若某批外部阻塞，记录后继续其他本地复验；
- 不因需要生产授权而停止全部本地工作；
- 最终用中文先给出两个结论：
  1. 本地整改候选是否通过；
  2. 生产发布是否为 GO 或 NO-GO。
- 随后列出七批结论、实际验证数字、发现/修复的问题、剩余风险和全部权威文件路径；
- 不要把“阅读了报告”描述为“验证了整改”，也不要把“本地通过”描述为“生产通过”。

开始执行时，先用一句话说明将进行独立复验，然后立即读取文件索引、记录工作树基线，
并进入第 1 批。
