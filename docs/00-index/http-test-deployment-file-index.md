# HTTP 测试部署文件索引

> 用途：作为 HTTP 子路径测试部署的文件路由、实现进度、验证证据和回滚同步入口。
> 状态：上一 deterministic HTTP release 已完成服务器验证；2026-07-29 性能
> 候选仅完成本地前端验证，尚未部署。Provider 预览、HTTPS、备份恢复和回滚
> 演练未执行，生产发布继续 NO-GO。
> 日期：2026-07-29。
> 权威性：本索引记录本任务事实，不替代当前审计报告、生产发布清单或服务器实际运行记录。

## 1. 阅读顺序

1. `docs/02-architecture/deployment/http-subpath-test-deployment-design.md`
2. `docs/01-overview/http-subpath-test-deployment-implementation-plan.md`
3. 本文件
4. `docs/04-operations/deployment/http-test-deployment-runbook.md`
5. 对应源码、测试和部署覆盖层
6. 本次重新运行产生的本地、CI 和服务器证据

## 2. 当前登记

| 文件 | 职责 | 状态 | 验证 | 回滚 |
| --- | --- | --- | --- | --- |
| `docs/02-architecture/deployment/http-subpath-test-deployment-design.md` | 已确认的架构、账号、助手、数据和运维边界 | 已新增 | 文档自审 | 删除该设计文件 |
| `docs/01-overview/http-subpath-test-deployment-implementation-plan.md` | 13 个按 TDD 执行的实现、验证、部署与人工检查任务 | 已新增 | 文件与接口复核；未执行计划内命令 | 删除该计划文件 |
| `docs/00-index/http-test-deployment-file-index.md` | 文件与证据同步入口 | 已新增 | 文档自审 | 删除该索引 |
| `docs/00-index/documentation-map.md` | 将本任务接入全项目文档地图 | 已更新 | 路径检查 | 删除 HTTP 测试部署入口 |
| `docs/06-evidence/platform/http-test-server-validation.json` | 服务器版本、路由、端口、隔离数据库、备份和 24 项脱敏全功能验证 | 已新增 | schema、秘密扫描和事实复核待最终门禁 | 删除该证据文件 |

设计阶段本身没有修改应用源码、测试、部署模板、Nginx、systemd、数据库或服务器文件；后续已实施范围及真实验证证据按批次登记如下。

## 3. 实现候选路由

下表由实施计划复核后用于约束下一阶段实现，不表示文件已经修改。每次修改后必须更新状态。

| 候选范围 | 预期职责 | 当前状态 |
| --- | --- | --- |
| `backend/app/core/config.py` | 通用公开前缀与独立 `http_test` 配置验证 | 候选，未修改 |
| `backend/app/main.py` | 复核 Nginx 剥离前缀后是否需要改动 | 已复核，无需修改；内部路径保持 `/api/v1`、`/uploads` 和 `/` |
| `backend/app/api/v1/routers/agent.py` | 登录会话所有权、游客隔离入口、replay 与有界历史上下文编排 | 已完成任务 4、任务 5及合并审查修复 |
| `backend/app/agent/schemas.py` | 严格的登录会话历史消息与游客请求契约 | 已完成任务 4、任务 5 |
| `frontend/assets/js/api.js` | 前缀感知的 API URL | 候选，未修改 |
| `frontend/assets/js/assistant-page.js` | 游客本地会话、草案和登录能力切换 | 已完成任务 6 及合并审查修复 |
| `frontend/assets/js/assistant-session-epoch.js` | 身份 epoch、会话异步操作取消与完成有效性 | 已新增；合并审查修复 |
| `frontend/assistant.html` | 游客状态与清除入口 | 已完成任务 6 |
| Users 授权与命令边界 | 唯一测试账号的身份、恢复、隐私和删除限制 | 候选，精确文件待实现计划复核 |
| `scripts/provision-http-test-account.py` | 无命令行秘密的一次性测试账号初始化 | 已完成任务 7 |
| `tests/` | 前缀、Agent 会话历史、测试账号限制、游客无服务端写入、初始化器、发布包和专项门禁回归 | 任务 1 至任务 10 已按范围更新 |
| `deploy/http-test/` | Nginx、systemd、项目选择页、无秘密环境模板和脚本 | 已完成任务 8，并在任务 9 纳入发布 allowlist；仅本地结构、shell 语法和发布包选择已验证 |
| `scripts/verify-http-test-deployment.ps1` | 顺序运行 Tasks 1–9 聚焦功能流并产生本次结构化计数 | 已完成任务 10；已接入 foundation 本地门禁和 CI |
| `scripts/build-http-test-server-validation.py` | 从脱敏服务器快照与交互验证报告生成严格服务器证据 | 已完成任务 13；拒绝额外敏感字段和不一致计数 |
| `docs/04-operations/deployment/http-test-deployment-runbook.md` | 参数化的备份、安装、初始化、验证、停止和回滚步骤 | 已完成任务 11并用于任务 13 部署；恢复、回滚和 Provider 章节未执行 |
| `docs/04-operations/deployment/http-test-deployment-troubleshooting.md` | 本次实机部署故障的现象、根因、推荐处理、验证和误判边界 | 已新增部署复盘；不包含秘密或生产成功声明 |
| `docs/06-evidence/platform/http-test-deployment-manifest.json` | 无内容、无秘密的本地专项门禁机器证据 | 已由任务 10 生成；所有外部验证仍为 `not_run` |
| `docs/06-evidence/platform/http-test-server-validation.json` | 任务 13 的脱敏服务器事实、24 项全功能流与分离结论 | 已由生成器写入并通过 schema/秘密扫描 |

### 3.1 实施批次：2026-07-26，任务 1（运行时配置档）

- 已修改 `backend/app/core/config.py`、`backend/run.py`、`tests/test_http_test_runtime.py` 与 `tests/test_agent_provider.py`：增加 `http_test` 和 `provider_preview` 的启动期安全契约，以及可验证的公共路径、监听地址和端口配置。
- `http_test` 保持确定性 Agent、关闭 live Provider、隔离持久化路径，并且仅允许显式 HTTP origin、非 Secure 的 lax refresh cookie 与固定公共前缀。
- `provider_preview` 仅允许 loopback 监听、独立的外部持久化路径和完整的 HTTPS/allowlist/北京地域 Provider 安全约束；端口必须合法但不被固定为某一数值。
- 本地回归已通过：隔离解释器的 unittest 运行 91 项测试；编译检查和 `git diff --check` 退出码均为 0。该解释器未安装 pytest，因此未将计划中的 pytest 命令误记为已运行。
- 服务器操作、真实 Provider 调用、HTTPS、备份恢复和生产验证均未执行。最小回滚路径为回退本批次提交。

### 3.2 实施批次：2026-07-26，任务 2（公开运行能力与公共路径投影）

- 已修改 `backend/app/platform/schemas.py`、`backend/app/api/v1/routers/common.py`、`frontend/assets/js/api.js`、`frontend/assets/js/auth-ui.js`、`frontend/assets/js/settings.js` 和对应测试；已新增 `frontend/assets/js/public-path.js` 与 `tests/test_public_path.mjs`。
- `/api/v1/runtime/public` 只公开部署档、公共前缀和布尔能力，不公开账号标识、持久化路径、Provider 配置或秘密。`http_test` 的注册、恢复、身份修改和隐私写能力均关闭；游客聊天与登录会话能力分别来自已校验配置。
- 浏览器 API、refresh、资料和头像 URL 统一从 `public-path.js` 派生；数据库头像字段仍保持 `/uploads/...`，只在浏览器显示边界添加 `/StarChart-AI`。绝对 URL、网络路径、遍历和重复前缀会被拒绝。
- `auth-ui.js` 与 `settings.js` 在能力端点返回前及失败时采用保守隐藏；资料、头像、偏好、登录会话与工作流界面保持可用，后端授权仍是最终边界。
- 本地 RED 证据：隔离解释器没有 pytest，计划中的 pytest 命令以 `No module named pytest` 退出；改用匹配的 unittest 命令后，新端点测试因 404 失败。Node 任务命令因缺少 `public-path.js`、能力投影函数和前缀 URL 而失败。
- 本地 GREEN 证据：`python -m unittest tests.test_http_test_runtime -v` 通过 8 项；任务 Node 命令通过 19 项；URL 安全与入口回归通过 14 项；`compileall` 和 `git diff --check` 退出码为 0。unittest 输出仍包含现有 FastAPI TestClient 的 Starlette 弃用警告。
- CI、服务器、真实 Provider、HTTPS、备份恢复和生产验证均未执行。最小回滚路径为回退任务 2 提交；无需修改数据库或迁移。

### 3.3 实施批次：2026-07-26，任务 3（测试账号服务端策略）

- 已新增 `backend/app/users/deployment_policy.py` 与 `backend/app/api/v1/dependencies/deployment_policy.py`，并在 auth、Users、privacy 路由入口集中执行 `http_test` 动作策略；领域策略不依赖 FastAPI，适配层统一映射 403 `DEMO_ACCOUNT_RESTRICTED`。
- `http_test` 只允许服务端配置并规范化后的唯一用户名登录；不存在账号、其他用户名及该账号的邮箱/手机别名均在认证服务和限流副作用之前统一拒绝。允许标识不进入错误消息，本索引和测试输出不记录真实账号凭据。
- 注册、用户名可用性、所有恢复/重置入口、身份/密码/安全问题修改、隐私同意/导出/删除请求及取消均由服务端拒绝。资料、头像、偏好、学习状态、登录会话、保存工作流、Agent 会话、退出和只读账号/资料/隐私状态保持原路由能力。
- 管理端 deletion execute/restore/anonymize 未接入测试账号策略，继续由原 `users:manage` 权限控制；专项测试证明普通测试账号仍被原权限系统拒绝。
- 本地 RED 证据：隔离解释器未安装 pytest，计划 pytest 命令以 `No module named pytest` 退出；匹配 unittest 的 5 项专项测试因策略模块缺失和危险路由仍可达而失败。
- 本地 GREEN 证据：匹配 unittest 专项与 Users 回归共 54 项通过；`scripts/verify-users.ps1` 在当前 PowerShell 进程中通过，其中 Users 服务 49 项、前端门禁、契约、安全、命令覆盖、迁移/恢复、性能和最终验收均成功。输出仍包含既有 FastAPI TestClient 的 Starlette 弃用警告。
- CI、服务器、真实 Provider、HTTPS、备份恢复和生产验证均未执行。最小回滚路径为回退任务 3 提交；无需修改数据库或迁移。

### 3.4 实施批次：2026-07-26，任务 4（登录会话有界对话上下文）

- 已修改 `backend/app/agent/schemas.py`、`backend/app/agent/sessions.py`、`backend/app/agent/providers/base.py`、`backend/app/agent/providers/__init__.py`、`backend/app/agent/providers/openai_compatible.py`、`backend/app/agent/orchestrator.py`、`backend/app/agent/governance.py`、`backend/app/agent/replay.py`、`backend/app/api/v1/routers/agent.py` 和四个 Agent 专项测试文件。
- 登录用户的短会话、长期会话与升级竞态源会话均复用现有消息表；历史严格限定为当前用户和会话的最新 12 条完整 `user`/`assistant` 消息，按时间正序返回，总字符数不超过 12,000，裁剪只从最旧端按整条消息执行。
- 路由在所有权验证后、生成前加载历史，并仅在成功且非 replay 的完成响应后追加一次新 exchange。Provider 消息顺序固定为 `system → bounded history → current user`；历史不进入 system、evidence、响应 meta 或日志，敏感历史仍受 Provider 输入校验。
- replay 指纹包含服务端解析后的有界历史；成功追加后用最新历史状态登记缓存，使直接重试可命中一次，而会话后续变化会保留原有 409 request-id 冲突语义。取消路径不追加、不缓存。
- Provider 治理输入预算同步计入历史字符，避免新增的最多 12,000 字符绕过既有 token/成本门禁。该窄修复对应“不得弱化任务 1 至任务 3 安全边界”，因此补充了原任务文件清单遗漏的 `backend/app/agent/governance.py`。
- RED 证据：隔离解释器没有 pytest，计划 pytest 命令以 `No module named pytest` 退出；匹配 unittest 首次运行的四个模块均因 `AgentHistoryMessage` / `ProviderConversationMessage` 尚不存在而导入失败。治理专项随后以历史 token 差值为 0 的断言失败，证明历史预算遗漏。
- GREEN 证据：四个聚焦 unittest 模块共 69 项通过；在一次性临时数据库上初始化 schema 与 migrations 后，`scripts/verify-agent.ps1` 通过 101 项 Python、3 项 Node/SSE、Python 编译、评估清单、盲评协议清单、模型决策基线、前端语法与 whitespace 检查；`git diff --check` 退出码为 0。
- 未读取真实 `.env`、凭据或用户内容，未调用真实 Provider/网络，未修改服务器、数据库 schema 或迁移。CI、服务器、HTTPS、备份恢复和生产验证均未执行。最小回滚路径为回退任务 4 提交。

### 3.5 实施批次：2026-07-26，任务 5（确定性游客助手入口）

- 已修改 `backend/app/agent/schemas.py`、`backend/app/api/v1/routers/agent.py`、`backend/app/agent/orchestrator.py`、`tests/test_agent_services.py`，并新增 `tests/test_agent_guest.py`。`POST /api/v1/agent/guest/chat` 不依赖 Authorization，只在 `APP_ENV=http_test` 且游客开关开启时放行；其他配置返回 404，并从对应 OpenAPI 文档隐藏。
- 游客请求复用任务 4 的 `AgentHistoryMessage`、orchestrator `history` 关键字与 replay fingerprint，不建立可选/伪造用户，不创建或追加 Agent session，不读取 Users Context，不保存或归档工作流。请求严格限制当前消息 4,000 字符、12 条 `user`/`assistant` 历史、单条 6,000 字符和历史总计 12,000 字符，并拒绝未知字段与不安全页面 URL。
- 游客编排显式执行 `provider_allowed=false`；专项测试向 orchestrator 注入会失败的 Provider 并证明不会调用。进程内游客 orchestrator 本身不读取 Provider 配置或工厂，因此误放 API key/live Provider 配置不能开启公网 Provider 路径。
- replay/admission 主体使用服务端 secret 对受信代理链解析后的客户端 IP 做 HMAC，仅保留 24 个十六进制摘要并使用独立 `guest:<digest>` 命名空间。专项测试检查 replay key、响应和 Agent 日志均不含原 IP 或消息正文；应用层继续保留 replay、全局/单 bucket 并发、队列和 15 秒请求超时边界。
- RED 证据：隔离解释器没有 pytest，计划 pytest 命令以 `No module named pytest` 退出；匹配 unittest 首次运行因游客 route、`AgentGuestChatRequest` 和 `respond_guest` 尚不存在，分别以 404、ImportError 和 AttributeError 失败。
- GREEN 证据：一次性临时数据库初始化后，`.\.venv\Scripts\python.exe -m unittest tests.test_agent_guest tests.test_agent_services tests.test_agent_observability -v` 的 27 项匹配 unittest 通过。另一次全新临时数据库上，当前 PowerShell 进程执行 `& .\scripts\verify-agent.ps1`，通过 108 项 Python、3 项 Node/SSE、Python 编译、评估清单、盲评协议清单、模型决策基线、前端语法与 whitespace 检查；`git diff --check` 退出码为 0。
- 首次未初始化数据库的 observability 回归因缺少 `tool_categories` 表失败；按 CI 方式初始化一次性隔离数据库后同一范围通过，未把该前置条件错误记为产品缺陷。Windows 环境没有可调用的 `powershell` 子进程且默认执行策略阻止脚本，最终在当前 PowerShell 进程使用仅进程级 Bypass 运行相同验证脚本。
- 未读取真实 `.env`、凭据或用户内容，未调用真实 Provider/网络，未修改服务器、数据库 schema 或迁移。Nginx 独立游客限流仍属于后续任务；在此之前 HTTP 测试候选继续为 `NO-GO`。最小回滚路径为回退任务 5 提交。

### 3.6 实施批次：2026-07-26，任务 6（浏览器游客记忆与身份模式切换）

- 已新增 `frontend/assets/js/guest-agent-memory.js` 与 `tests/test_guest_agent_memory.mjs`，并修改 `frontend/assets/js/assistant-page.js`、`frontend/assistant.html`、`tests/test_agent_frontend.mjs` 和 `tests/test_auth_ui.mjs`。版本化键 `ai-nav:guest-agent:v1` 只保存游客会话消息，不保存 Token、账号资料或服务端标识。
- 游客存储每次读取都会校验 schema、安全 role、7 天 TTL、最多 10 个会话和每会话 40 条消息；损坏 JSON、错误版本或不安全 role 会自愈为空。发往游客端点的当前会话历史保持完整消息边界，最多 12 条、合计不超过 12,000 字符；清除入口只删除本应用游客键并要求浏览器二次确认。
- `assistant-page.js` 只以 `getAccessToken()` 和 `ai-nav-auth-changed` 决定模式。未登录请求固定发送至 `/agent/guest/chat`，不调用服务端 session、升级、归档或工作流保存入口；登录后继续使用原 `/agent/chat`、stream、sessions 与 workflows。登录事件不导入、不删除也不发送游客历史，退出后重新显示原浏览器游客历史，已登录写请求的 401 不会静默降级为游客写。
- 游客工作流草稿可在页面内创建和编辑，但保存入口保持禁用并明确说明不能保存/归档且登录不会自动导入。游客消息仅在响应成功后成对写入本地历史；失败时保留显式重试或恢复输入，不向本地历史追加失败 exchange。
- RED 证据：首次任务 Node 命令运行 9 个测试单元，其中 6 个通过、3 个按预期因游客存储模块、游客端点/UI 分支和身份事件处理尚不存在而失败。GREEN 证据：`node --test tests/test_guest_agent_memory.mjs tests/test_agent_frontend.mjs tests/test_auth_ui.mjs tests/test_agent_sse.mjs` 通过 17 个测试单元；当前 PowerShell 进程使用仅进程级 Bypass 执行 `scripts/verify-frontend.ps1`，通过 31 项前端入口回归、JavaScript 语法与 whitespace 检查；`git diff --check` 退出码为 0。
- 计划中的 `powershell -ExecutionPolicy Bypass -File scripts/verify-frontend.ps1` 因当前 Windows 环境没有可调用的 `powershell` 子进程而未启动；随后在当前 PowerShell 进程执行相同脚本并通过。CI、服务器、真实 Provider、网络、HTTPS、备份恢复和生产验证均未执行；未读取真实 `.env` 或凭据，未修改后端、数据库、迁移或服务器。最小回滚路径为回退任务 6 提交。

### 3.7 修复批次：2026-07-26，Tasks 4–6 Agent 全流程审查

- 已新增 `frontend/assets/js/assistant-session-epoch.js`，并修改 `frontend/assets/js/assistant-page.js`、`backend/app/agent/replay.py`、`backend/app/api/v1/routers/agent.py` 及对应 Agent、游客和认证前端测试。没有数据库 schema、migration、Provider、网络、服务器或部署覆盖层变更。
- 浏览器以访问令牌中的稳定 `sub` 判断真实身份转换；游客与用户、不同用户之间的转换会推进 epoch 并中止全部在途会话列表、详情、创建、删除、置顶、升级、重命名、能力初始化和聊天操作。每个异步完成点在改变 DOM 或页面状态前核对捕获的 epoch；同一 `sub` 的令牌刷新不推进 epoch、不取消当前操作，也不重置当前会话。
- Agent replay 使用只含摘要的 `(principal, request_id)` 进程内 key，并以引用计数的逐 key single-flight 覆盖所有权/历史解析、replay 查询、生成、exchange 追加和 replay 完成。相同 key 的相同请求只生成、追加和缓存一次，跟随者复用首个结果；不同 payload 在首个完成后按完整历史指纹返回 409。不同 key 可并行，完成后 key 立即释放，不使用覆盖生成过程的全局粗锁，也不保留无界 key。
- exchange 追加、追加后历史解析与 replay 写入由 cancellation-shielded finalizer 完成；取消发生在生成完成前时保持“未追加、未缓存”，发生在追加后完成阶段时会先完成 replay 再传播取消，避免“已追加但不可 replay”的中间状态。登录和游客入口均复用同一 single-flight 边界。
- RED 证据：`node --test tests/test_auth_ui.mjs` 首次运行 10 项中 7 项通过、3 项因身份 epoch 模块尚不存在而失败；随后 mutation check 临时移除 epoch 推进/中止，同一命令 10 项中 8 项通过、2 项按预期显示旧用户会话标题、消息和 session ID 会写入新模式。三个聚焦 replay unittest 首次全部失败：相同并发请求发生重复生成/缓存冲突，不同 payload 生成次数为 2 而非 1，取消后出现已追加但缓存为空。
- GREEN 证据：`.\.venv\Scripts\python.exe -m unittest tests.test_agent_replay tests.test_agent_sessions tests.test_agent_guest -q` 通过 29 项；`node --test tests/test_guest_agent_memory.mjs tests/test_agent_frontend.mjs tests/test_auth_ui.mjs tests/test_agent_sse.mjs` 通过 20 项；恢复 mutation 后 `node --test tests/test_auth_ui.mjs` 通过 10 项。
- 全门禁证据：当前 PowerShell 进程执行 `scripts/verify-frontend.ps1`，通过 34 项前端测试、JavaScript 语法和 whitespace；在系统临时目录创建并初始化一次性数据库后执行 `scripts/verify-agent.ps1`，通过 112 项 Python、3 项 Node/SSE、Python 编译、评估清单、盲评协议清单、模型决策基线、前端语法与 whitespace。临时数据库随后删除；最终 `git diff --check` 退出码为 0。
- 未读取真实 `.env`、凭据、Token 或用户内容，未调用真实 Provider、网络或服务器。CI、HTTPS、备份恢复、服务器验收和生产验证仍未执行；HTTP 测试候选与生产发布结论继续为 `NO-GO`。最小回滚路径为回退本修复批次提交，无需数据库回滚。

### 3.8 实施批次：2026-07-26，任务 7（无秘密测试账号初始化）

- 已新增 `scripts/provision-http-test-account.py` 与 `tests/test_provision_http_test_account.py`。初始化器强制关闭 dotenv 加载，仅允许 `http_test`/`provider_preview` 配置档，仅接受交互式用户名和隐藏密码输入，并拒绝命令行参数、密码环境变量与非 TTY 标准输入。
- 数据库和上传目录在写入前解析并验证为源码树外路径。初始化在同目录临时数据库中执行现有 schema、seed、迁移与 `AuthenticationService` 注册/哈希流程；现有任意账号会拒绝执行，注册生成的 refresh session 会立即经现有认证服务撤销，成功验证后才原子替换目标数据库。失败会删除暂存数据库及本次新建的空上传目录，不留下半初始化账号。
- 成功返回与控制台仅包含脱敏状态、用户 UID 的 12 位 SHA-256 摘要和外部路径已验证状态，不返回或打印登录标识、密码、密码哈希、access/refresh token。测试夹具只使用明确命名的合成值，不包含用户提供的测试账号或任何真实凭据。
- RED 证据：计划中的 `.\.venv\Scripts\python.exe -m pytest tests/test_provision_http_test_account.py -q` 因隔离解释器未安装 pytest，以 `No module named pytest` 退出；匹配 unittest 随后因目标脚本尚不存在而以 `FileNotFoundError` 失败。
- GREEN 证据：`.\.venv\Scripts\python.exe -m unittest tests.test_provision_http_test_account -v` 通过 7 项；设置 `PYTHONPATH=backend` 后，`.\.venv\Scripts\python.exe -m unittest tests.test_provision_http_test_account tests.test_users_services -q` 通过 56 项，最终运行耗时 23.950 秒。首次未设置 `PYTHONPATH` 的合并回归因无法导入 `app` 快速退出，修正测试环境后同一范围通过；Users 回归仍输出既有 Starlette TestClient 弃用警告。
- 未读取真实 `.env`、真实账号、凭据或用户数据，未调用 Provider、网络或服务器；未对实际数据库执行初始化。CI、服务器、HTTPS、备份恢复、真实回滚和生产验证仍未执行。最小回滚路径为回退任务 7 提交；若仅回滚一次真实初始化，应在服务停止且已备份的前提下移除该隔离测试数据库和空上传目录，而不是修改项目数据库。

### 3.9 实施批次：2026-07-26，任务 8（隔离 HTTP 测试部署覆盖层）

- 已新增 `deploy/http-test/` 下的两个空敏感值环境模板、Nginx 覆盖配置、两个 systemd 单元、项目选择页和三个部署辅助脚本，并新增 `tests/test_http_test_overlay.py`。覆盖层不包含公网 IP、账号、密码、可用服务端密钥、API Key、数据库、上传内容或本机绝对路径。
- Nginx 只使用 `127.0.0.1:8000` 与 `127.0.0.1:8001` 两个具名 upstream，未提供 8002 公网 location；`/StarChart-AI` 与 `/old-ai-nav` 规范化到尾斜杠，前者剥离前缀并设置 `X-Forwarded-Prefix`。游客端点使用独立 `10r/m`、`burst=5 nodelay`、64 KiB 请求体和 20 秒读写超时。旧 `/chat`、`/health`、`/chat-widget.js` 精确路由位于项目选择页静态回退之前。
- 项目选择页只链接相对的旧站与 StarChart-AI 两张卡片，不包含脚本、追踪器或内联秘密。旧站如果还依赖未登记的根相对静态资源，必须在服务器只读预检中按实际资源添加精确兼容路由；当前覆盖层有意不增加会覆盖项目选择页的宽泛旧站 fallback。
- 两个 systemd 单元都以专用非 root 用户运行，固定 `AI_NAV_API_WORKERS=1`，启用 `NoNewPrivileges`、`PrivateTmp` 和只读应用目录，只允许各自的 `/srv` 数据根写入。公网单元固定 8001、deterministic/live off；预览单元固定 loopback 8002、独立数据库和上传目录且没有默认自动启动目标。
- `install-overlay.sh` 只安装仓库模板、先备份现有 Nginx 配置并仅在 `nginx -t` 成功后 reload，不生成秘密；公网与 Provider 预览分别使用 `starchart-ai-http-test`、`starchart-ai-provider-preview` 身份、私有数据目录和专属环境文件组，systemd 显式屏蔽对方目录与环境文件。`preflight.sh` 以 `before-first-start`/`before-provider-preview` 阶段契约解析 `ss` 行并检查旧 8000 存在、新端口处于预期状态，同时只读检查目录、环境文件权限、数据库路径隔离和 Nginx 语法；`smoke-test.sh` 只访问本机 8001 健康路径及经本机 Nginx 的公开 deterministic 页面和运行能力端点，不创建账号、不访问 8002。
- RED 证据：计划中的 `.\.venv\Scripts\python.exe -m pytest tests/test_http_test_overlay.py -q` 因隔离解释器未安装 pytest，以 `No module named pytest` 退出；匹配 unittest 首次运行 11 项，其中 10 项因覆盖层文件不存在而失败、1 项空目录扫描通过。
- GREEN 证据：`.\.venv\Scripts\python.exe -m unittest tests.test_http_test_overlay -v` 通过 11 项。Windows 的 WSL `bash` 入口因本机实例权限错误未能运行；随后使用本机 Git for Windows Bash 对三个脚本执行相同 `bash -n` 语法验证，两套 Git Bash 入口均退出码 0。
- 当前环境不存在可调用的 Nginx 和 `systemd-analyze`，所以真实 `nginx -t -c <staged-config>` 与 systemd unit 加载验证均为 `NOT RUN`。未执行脚本、未访问网络或服务器、未调用 Provider、未读取真实 `.env`，也未进行实际备份、reload、smoke、部署或回滚。最小回滚路径为回退任务 8 提交；覆盖层尚未部署，因此不涉及服务器或数据回滚。

### 3.10 实施批次：2026-07-26，任务 9（发布包覆盖层与秘密排除）

- 已修改 `scripts/build-release-package.ps1`，把 `deploy/http-test` 加入明确允许根目录，并把运行时所需的 `scripts/provision-http-test-account.py` 与发布内容扫描器加入固定单文件清单；发布选择继续从固定根目录和固定单文件清单开始，不扫描仓库根目录或用户临时文件。选择完成和暂存完成后都会对精确成员运行脱敏内容扫描，只有已知图片扩展名允许二进制/大文件。`ValidateOnly` 仅输出不含内容的计数，本次真实工作树结果为 `fileCount=365`、`forbiddenCount=0`、`deploymentOverlayCount=10`。
- 发布脚本现在先枚举每个允许根目录，再对秘密、运行时数据库、上传内容、日志、备份和 Provider 响应证据执行 fail-closed 检查，不再把这些高风险产物静默过滤后继续构建。环境文件只对文件名为 `env.example` 或以 `.env.example` 结尾的模板开放显式例外；模板内容仍由后续任务 10 的秘密扫描器负责检查。
- 已新增 `tests/test_release_http_test_overlay.py` 并扩展 `tests/test_http_test_overlay.py`。测试在系统临时目录创建完全合成的最小发布树，验证覆盖层和环境模板进入 zip，普通 `.env`、`.sqlite3`、uploads、备份、日志、systemd 实际环境文件和 Provider 响应证据均使构建失败，并确认 `.tmp_ci.txt`、`.tmp_push_ci.txt`、`.git`、测试结果和本机绝对路径不进入 zip。
- RED 证据：计划中的 `.\.venv\Scripts\python.exe -m pytest tests/test_release_http_test_overlay.py tests/test_http_test_overlay.py -q` 因隔离解释器未安装 pytest，以 `No module named pytest` 退出；匹配 unittest 首次运行 16 项，按预期暴露覆盖层未入包、缺少 `deploymentOverlayCount`，以及 7 类禁止产物被静默跳过。
- GREEN 证据：`.\.venv\Scripts\python.exe -m unittest tests.test_release_http_test_overlay tests.test_http_test_overlay -v` 通过 16 项，最近一次耗时 6.523 秒；`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-release-package.ps1 -ValidateOnly` 退出码 0 并返回上述三个真实计数；`git diff --check` 退出码 0。
- 未读取真实 `.env` 或凭据，未调用网络、服务器或 Provider，未生成或部署真实发布版本，Linux Nginx/systemd、HTTPS、备份恢复、服务器 smoke 和回滚仍为 `NOT RUN`。最小回滚路径为回退任务 9 提交；发布包尚未部署，因此不涉及服务器或数据回滚。

### 3.11 实施批次：2026-07-26，任务 10（专项门禁与无秘密机器证据）

- 已新增 `scripts/verify-http-test-deployment.ps1`、`scripts/build-http-test-deployment-manifest.py`、`scripts/check-no-secrets.py`、两项专项测试和 `docs/06-evidence/platform/http-test-deployment-manifest.json`，并把专项门禁接入 `scripts/verify-foundation.ps1`；foundation CI 增加部署覆盖层和平台证据的路径触发，原 quality/foundation/agent 三个 job 的拆分不变，未注入测试账号密码或 Provider key。
- 门禁使用一次性运行 ID、系统临时目录和临时数据库，顺序运行 Tasks 1–9 的 Python/Node 功能范围、发布包 `ValidateOnly` 和秘密扫描。每组计数从本次进程输出写入严格结构化结果；生成器只接受名称、schema 和运行 ID 全部匹配的七组结果，任一失败都在原子替换前退出并保留上一份通过证据。
- 秘密扫描器支持文件和目录的显式项目内路径，只报告相对文件、行号和规则名，不回显匹配值；真实 `.env`、数据库、uploads、二进制、超大文件和项目外路径在读取内容前 fail closed。测试夹具只使用代码中拼接且标记为 `synthetic-test-only` 的合成值；未读取任何真实 `.env`。
- RED 证据：计划中的 `.\.venv\Scripts\python.exe -m pytest tests/test_http_test_manifest.py tests/test_no_secrets.py -q` 因隔离解释器未安装 pytest，以 `No module named pytest` 退出；匹配 unittest 首次运行 8 项，因构建器和扫描器不存在出现 1 个失败、4 个错误。首次门禁集成还分别暴露 Windows PowerShell 将既有 stderr 警告提升为终止错误、结构化 JSON 带 BOM 两个兼容边界；两次均在 manifest 写入前失败，未覆盖证据。
- GREEN 证据：最近一次定向 overlay/release/scanner 组合测试通过 26 项。最近一次完整 `scripts/verify-http-test-deployment.ps1` 退出码 0，本次真实计数为 runtime 49、policy 8、agentHistory 74、guestAgent 27、frontend 47、overlay 20、release 6；发布验证返回 `fileCount=365`、`forbiddenCount=0`、`deploymentOverlayCount=10`。
- 机器证据的 `sourceCommit` 为 `WORKTREE`，`containsSecrets=false`；`serverDeployment`、`providerPreview`、`https`、`backupRestore` 和 `rollback` 全部保持 `not_run`。未访问网络、服务器或 Provider，未执行部署、HTTPS、备份恢复或回滚。最小回滚路径为回退任务 10 提交；证据为生成文件，不代表服务器或生产通过。

### 3.12 实施批次：2026-07-27，任务 11（运行手册与文档治理）

- 已新增 `docs/04-operations/deployment/http-test-deployment-runbook.md`，并同步设计实施对应表、文件索引、文档地图和 README 文档入口。
- 运行手册按备份、只读预检、不可变发布安装、root 交互编辑、唯一账号初始化、8001 启动、Nginx 语法验证/reload、确定性 smoke、8002 loopback 手工预览、停止和最小回滚组织。每组服务器命令均标明执行身份和工作目录，实际值使用变量或占位符。
- 两个 EnvironmentFile 在填写前要求收紧为 root-only `0600`；文档不包含真实 IP、账号、密码、API Key、Cookie 或 Token，也不要求在命令行、环境变量或聊天中传递密码/API Key。
- 手册明确 HTTP 可窃听风险、禁止真实隐私数据、登录不自动导入游客历史，以及本地整改候选、HTTP 测试部署、真实 Provider 预览、生产发布四个独立结论。生产发布保持 `NO-GO`。
- 本任务只进行面向人工执行的结构化审查，不新增脆弱的 Markdown 源文本断言。运行手册引用的脚本、配置和路由由任务 1–10 的行为测试负责；本次文档链接、秘密扫描和差异检查结果记录于本节后续命令结果。
- 使用隔离临时数据库运行 `scripts/check-content-links.py`，离线检查 238 个已发布引用（Learning 104、Tools 134），退出码 0；`git diff --check` 退出码 0。
- 计划中的整目录秘密扫描 `scripts/check-no-secrets.py --paths docs deploy README.md` 按 fail-closed 规则命中 `docs/06-evidence/users/screenshots/` 内 4 个既有 PNG 二进制证据，退出码 1；这些文件不是本任务新增或修改，未删除、移动或豁免。随后对本任务五个文档文件、`deploy/` 和 `README.md` 运行相同扫描器，未发现秘密形状值或禁止制品，退出码 0。
- 未访问网络、服务器或 Provider，未执行部署、Nginx/systemd 变更、真实 Provider、HTTPS、备份恢复或回滚。最小回滚路径为回退任务 11 提交；无数据库或服务器回滚需求。

### 3.13 复验批次：2026-07-28，任务 12（最终本地门禁与全功能负向流）

- 已把隔离分支的 16 个已审计提交按原顺序合并到当前功能分支；保留并未读取、移动、暂存或修改工作区既有的 `.tmp_ci.txt`、`.tmp_push_ci.txt`。
- 最终门禁暴露并修复五类本地事实缺口：Ruff 中途导入与未使用导入、OpenAPI 操作/响应模型基线计数滞后、`dependencies` 包级重导出导致的认证路由循环导入、显式 Python 与损坏旧 `.venv` site-packages 混用、专项门禁和发布构建器重复选择错误 Python。新增 `tests/test_python_runtime.py`，明确验证显式解释器不混入另一虚拟环境。
- Windows 子进程编码夹具显式设置 `PYTHONUTF8=1`；测试中的 Bearer、私钥头和密码夹具改为等价的合成拼接形式，使分支秘密扫描不需要放宽规则。相关 Agent Provider、初始化器、秘密扫描、Python 运行时和前端夹具回归合计 65 项通过。
- `scripts/verify-quality.ps1` 在源码外临时数据库上通过：Ruff 通过、Python 依赖审计报告 0 个已知漏洞、发布选择 `fileCount=365`/`forbiddenCount=0`/`deploymentOverlayCount=10`、252 项 Python 测试通过，分支覆盖率 86.5%。
- `scripts/verify-agent.ps1` 在 CI 同等初始化的临时数据库上通过 112 项 Python 和 3 项 Node/SSE；`scripts/verify-frontend.ps1` 通过 34 项；`scripts/verify-users.ps1` 通过 49 项服务测试及前端、35 项命令安全、20 项迁移、8 项性能操作和 3 项查询计划；`scripts/verify-foundation.ps1` 最终退出码 0。
- `scripts/verify-http-test-deployment.ps1` 最终退出码 0，本次真实计数为 runtime 49、policy 8、agentHistory 74、guestAgent 27、frontend 47、overlay 20、release 6；机器证据由本次结构化结果原子替换。独立发布校验再次返回 365/0/10。
- 负向全功能流通过 5 项：游客请求不创建 Users/session/workflow 数据且不调用 Provider、配置了 Provider 时游客仍强制 deterministic、唯一测试账号限制在副作用前拒绝、允许的账号功能继续可用、跨用户 Agent session 与不存在资源不可区分。
- 对当前分支相对计划基线的 76 个实际文件运行脱敏秘密扫描，结果为 0 命中；发布成员另由构建器在选择和暂存两个阶段扫描。所有临时数据库和路径清单均已删除，未读取真实 `.env`，未调用真实 Provider。
- 本地整改候选结论为 `GO`。Linux Nginx/systemd 加载、服务器部署、真实 Provider 预览、HTTPS、服务器备份恢复与回滚在任务 13 执行前仍为 `NOT RUN`；HTTP 服务器部署和生产发布仍保持 `NO-GO`。

### 3.14 部署批次：2026-07-28，任务 13（deterministic HTTP 测试服务器）

- 已按人工授权在目标服务器完成旧站备份、不可变 release 安装、独立 Python 运行时与 systemd 服务、Nginx 子路径覆盖、隔离数据库和唯一普通测试账号初始化；发布目录当前指向提交 `0025cbb0403659995374be09b239b839d751d341`，发布包 SHA-256 为 `b45da8e56bdbf0d05d1bda9253c91baa53f4b76b4ed79303f0c3ff73a83e8dbc`。
- 部署过程中发现并最小修复四个真实缺口：Linux shell 的 CRLF、未实现的 Agent runtime state backend 配置值、旧站小组件精确 Nginx 路由、HTTP 测试档遗漏登录 Agent sessions；最终又以 RED/GREEN 回归修复创建重复空会话时 `AgentSessionError` 未映射为 HTTP 409 的路由缺口。对应最终修复提交为 `0025cbb`，HTTP 策略 8 项和 Agent 会话 11 项在服务器临时源码目录通过。
- Nginx 语法检查和 deterministic smoke 通过；旧 8000 保持原监听，公网实例 8001 仅监听 `127.0.0.1`，8002 关闭。项目选择页、旧站、旧健康、旧小组件、新站、API 健康和公开运行能力七个路径本次均返回 200。
- 隔离数据库权限为 `0600`，归专用服务账号所有，账号数量只读复核为 1。旧站备份归档存在且 `gzip -t` 通过；这只证明归档完整，不等于恢复已验证。
- 交互式测试账号全功能验证 24/24 通过：登录与刷新、账号/资料/偏好读取和允许修改、头像、登录会话、工作流创建/归档/恢复、既有空 Agent 会话恢复、正常对话、会话修改/升级/长期会话读取与删除、退出、游客有界历史对话和匿名账号拒绝。脱敏报告 SHA-256 为 `a8975315d58be72837fc5cb99aeea4eb0e824f06ad035dc2cb7bc1ccc5a1ba64`，没有记录账号标识、密码、Token、Cookie、请求正文或响应正文。
- 服务器机器证据写入 `docs/06-evidence/platform/http-test-server-validation.json`。真实 Provider 调用、8002 预览、HTTPS、容量、合规、备份恢复、回滚演练和外部生产签收均为 `NOT RUN`。
- 已新增 `scripts/build-http-test-server-validation.py` 与 `tests/test_http_test_server_validation.py`；生成器只接受固定脱敏 schema、通过且计数一致的交互验证报告、完整 commit/SHA-256 和获批端口/数据库/备份边界，额外账号或敏感字段会拒绝且不写输出。RED 为生成器不存在时 2 项中 1 项失败；GREEN 为 2/2 通过。
- 最终复验使用服务器 `/tmp` 中的同提交临时源码副本和隔离 Python 3.12 运行 Python 专项组，分别通过 runtime 49、policy 8、agentHistory 74、guestAgent 27、overlay 22 项；overlay 首次在 Linux 暴露文件枚举顺序断言，改用 `assertCountEqual` 后 22/22 通过。Windows 专属 release 组回到本机运行并通过 7/7，本机 Node 前端组通过 47/47；生成器 2/2、Ruff、Python 编译、发布 allowlist 365/0/10、定向秘密扫描和 `git diff --check` 均通过。本机旧 `.venv` 的解释器目标已丢失，因此没有把本次服务器 Python 专项误记成完整本地 quality 门禁；应用源码仅有已部署的 409 路由修复，相关 HTTP/Agent 专项已覆盖。
- 当前结论分别为：本地整改候选 `GO`；deterministic HTTP 测试部署 `GO`；真实 Provider 预览 `NOT RUN`；生产发布 `NO-GO`。最小应用回滚路径是把 `/opt/starchart-ai/current` 指回上一不可变发布并重启 8001；覆盖层或旧站恢复没有实际演练，因此不能宣称回滚通过。

### 3.15 文档批次：2026-07-28，部署故障复盘

- 已新增 `docs/04-operations/deployment/http-test-deployment-troubleshooting.md`，将本次真实出现的 SSH、终端回显、CRLF、解压工具、Python/依赖、runtime backend、systemd 就绪、Nginx 子路径与旧站精确路由、SQLite、Agent 空会话、Windows SCP、脱敏报告和验证时长问题整理为快速定位表及分层排查步骤。
- 每个问题均区分现象、根因、推荐处理、验证和误判边界；没有记录主机地址、账号标识、密码、Token、Cookie、真实 `.env` 或 Provider 内容。
- 备份完整性、恢复、回滚、deterministic Agent、真实 Provider 和生产发布保持分离结论；未执行的事项继续标记为 `NOT RUN`。
- 本批次只修改 Markdown 导航与故障文档；验证只运行文档秘密扫描、显式路径检查和 `git diff --check`，不复用或重复运行与文档无关的长测试套件。

### 3.16 Git 与 HTTP 隐私复核：2026-07-29

- 当前权威记录为 `docs/05-quality/audits/git-http-privacy-audit.md`。
- HTTP 文件不再记录真实服务器 origin、本机绝对路径、测试账号标识或 SSH 登录串；运行时测试使用 RFC 5737 文档保留地址。
- 发现首次仓库根目录迁移仍继承旧父仓库历史，已创建干净 subtree 候选并保持现有 `master` 可恢复；默认分支是否再次替换必须以候选发布与确认结果为准。
- 本次 HTTP 专项门禁以隔离 Python 重跑并通过 runtime 49、policy 8、agentHistory 74、guestAgent 27、frontend 47、overlay 22、release 7；发布选择为 366/0/10。

### 3.17 性能批次：2026-07-29，助手与全站启动/交互优化

- 权威复验记录为 `docs/05-quality/audits/http-test-assistant-site-performance-20260729.md`；设计和执行清单分别位于 `docs/superpowers/specs/2026-07-29-assistant-and-site-performance-design.md` 与 `docs/superpowers/plans/2026-07-29-assistant-and-site-performance.md`。
- 已将无确定性答案的默认比较问题改为“RAG 怎么学？”，并完成助手 SSE 帧缓冲、短/长期列表分区后台刷新、请求版本隔离和 `DocumentFragment` 批量挂载。
- 已完成公共页面非阻塞认证启动、搜索去抖/取消/最新结果、学习页并行水合、全站滚动/悬停帧合并、屏外绘制跳过、关键 module preload、352 B 指纹品牌图和 Nginx gzip/精确 immutable 缓存。
- 本次真实 Node 全集为 73/73，正式前端门禁为 58/58，所有目标 JavaScript 语法与 `git diff --check` 通过。完整质量门禁运行 259 项 Python 测试，分支覆盖率 86.4%，Ruff 与依赖审计通过；发布选择为 367/0/10。
- Foundation 门禁通过；HTTP 专项门禁最新七组计数为 runtime 49、policy 8、agentHistory 74、guestAgent 27、frontend 71、overlay 22、release 7。机器证据保持 `sourceCommit=WORKTREE` 且 `containsSecrets=false`。
- 普通 8088 实例的 10 个清单路径全部为 200。本地 Playwright 复验覆盖桌面五页、390×844 助手页、游客 deterministic 问答/草稿/设置门禁，以及临时合成账号注册、短会话创建和登录会话问答；临时实例和数据库已删除。
- 当前 performance worktree 的前端实现候选和完整仓库本地候选均为 `GO`，本次 HTTP release 为 `NOT DEPLOYED`，生产发布为 `NO-GO`。上一已部署 release 的历史 `GO` 仍只对其自身有效。

### 3.18 执行交接：2026-07-29，本地部署复验与 Git

- 当前执行入口为 `docs/01-overview/assistant-site-performance-local-deploy-git-handoff-20260729.md`。
- 交接记录原工作目录的命名分支、当前 HEAD、detached Codex worktree、已完成实现、
  73/73 与 58/58 前端证据，以及本轮新增的 Python、浏览器和 8088 本地运行证据。
- 本轮已经在原工作目录完成本地源码、运行实例、正式门禁与浏览器复验；后续从
  文档同步、精确 Git 审计、功能分支提交和 CI 继续。不得从 detached worktree
  直接 push，不得用历史通过代替当前验证。
- 当前性能候选 HTTP 仍为 `NOT DEPLOYED`，生产发布仍为 `NO-GO`。

## 4. 强制同步字段

每次实现或部署更新都必须追加：

- 批次与日期；
- 实际修改文件；
- 设计条款；
- 本次真实测试命令与结果；
- CI 运行链接与真实数字；
- 服务器操作是否已执行；
- Provider、HTTPS、备份恢复和回滚是否有真实证据；
- 残留风险；
- 最小回滚路径。

禁止把计划命令写成已执行结果，也禁止用本地测试代替服务器或生产验证。

## 5. 秘密与测试数据

本索引及其链接文档不得记录：

- 预置测试账号的用户名或密码；
- 真实 API Key 或服务端密钥；
- Authorization、Cookie、Token 或 SSH 私钥；
- 真实用户内容、Provider 请求或回答正文；
- 未脱敏服务器日志。

凭据只允许通过服务器端受限配置或一次性交互式命令注入。

## 6. 当前结论

- 设计：已由用户确认。
- 实施计划：共 13 个顺序任务；任务 1 至任务 13 已完成 deterministic HTTP 部署范围。
- 应用实现：任务 1 的运行时配置档、任务 2 的公开运行能力与公共路径投影、任务 3 的测试账号服务端策略、任务 4 的登录会话有界对话上下文、任务 5 的确定性游客助手后端入口、任务 6 的浏览器游客记忆与身份模式切换和任务 7 的无秘密测试账号初始化器已完成；任务 8 没有修改应用源码。
- 部署覆盖层：已创建并纳入 deny-first 发布包；本地结构测试、shell 语法和发布选择通过，Linux Nginx/systemd 加载验证仍为 `NOT RUN`。
- 本地专项测试：任务 1 至任务 10 已按各自范围运行并通过；任务 11 只执行文档链接、秘密扫描、差异检查和人工结构审查；最新专项门禁七组真实计数已写入无秘密 manifest。
- 全量门禁：已于 2026-07-29 在原工作目录重新运行并通过；质量门禁 259 项、覆盖率 86.4%，专项门禁七组计数为 49/8/74/27/71/22/7，发布选择为 367/0/10。
- 服务器部署：deterministic 8001 实例已执行并通过本次 smoke、公开路由、隔离边界和 24 项账号/游客全功能验证。
- 上一已部署 release 的本地整改候选：`GO`；2026-07-29 performance worktree 的完整仓库本地候选：`GO`。
- HTTP 服务器部署：上一已验证 release 为 `GO`，仅限当前无 HTTPS、无真实隐私数据、无 live Provider 的测试用途；2026-07-29 performance worktree 为 `NOT DEPLOYED`，备份恢复和回滚演练仍为 `NOT RUN`。
- 真实 Provider 预览：`NOT RUN`，8002 保持关闭。
- 生产发布：`NO-GO`，HTTPS、外部签收和生产证据仍缺失。
