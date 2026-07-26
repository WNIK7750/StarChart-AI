# HTTP 测试部署文件索引

> 用途：作为 HTTP 子路径测试部署的文件路由、实现进度、验证证据和回滚同步入口。
> 状态：设计与实施计划已完成；任务 1 至任务 6 已完成，Tasks 4–6 Agent 全流程审查发现的两项 Important 竞态已在本地修复并验证；部署覆盖层和服务器尚未修改。
> 日期：2026-07-26。
> 权威性：本索引记录本任务事实，不替代当前审计报告、生产发布清单或服务器实际运行记录。

## 1. 阅读顺序

1. `docs/02-architecture/deployment/http-subpath-test-deployment-design.md`
2. `docs/01-overview/http-subpath-test-deployment-implementation-plan.md`
3. 本文件
4. 后续 HTTP 测试部署运行手册
5. 对应源码、测试和部署覆盖层
6. 本次重新运行产生的本地、CI 和服务器证据

## 2. 当前登记

| 文件 | 职责 | 状态 | 验证 | 回滚 |
| --- | --- | --- | --- | --- |
| `docs/02-architecture/deployment/http-subpath-test-deployment-design.md` | 已确认的架构、账号、助手、数据和运维边界 | 已新增 | 文档自审 | 删除该设计文件 |
| `docs/01-overview/http-subpath-test-deployment-implementation-plan.md` | 13 个按 TDD 执行的实现、验证、部署与人工检查任务 | 已新增 | 文件与接口复核；未执行计划内命令 | 删除该计划文件 |
| `docs/00-index/http-test-deployment-file-index.md` | 文件与证据同步入口 | 已新增 | 文档自审 | 删除该索引 |
| `docs/00-index/documentation-map.md` | 将本任务接入全项目文档地图 | 已更新 | 路径检查 | 删除 HTTP 测试部署入口 |

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
| `tests/` | 前缀、Agent 会话历史、测试账号限制和游客无服务端写入回归 | 任务 1 至任务 6 已按范围更新 |
| `deploy/http-test/` | Nginx、systemd、项目选择页、无秘密环境模板和脚本 | 候选，未创建 |
| `docs/04-operations/` | 后续部署、验证、备份与回滚运行手册 | 候选，未创建 |
| `docs/06-evidence/` | 后续脱敏机器证据 | 候选，未创建 |

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
- 实施计划：已完成，共 13 个顺序任务；任务 1 至任务 6 已完成，其余任务尚未执行。
- 应用实现：任务 1 的运行时配置档、任务 2 的公开运行能力与公共路径投影、任务 3 的测试账号服务端策略、任务 4 的登录会话有界对话上下文、任务 5 的确定性游客助手后端入口和任务 6 的浏览器游客记忆与身份模式切换已完成；其余应用功能尚未开始。
- 部署覆盖层：未创建。
- 本地专项测试：任务 1 至任务 6 已运行并通过；其余专项测试未运行。
- 全量门禁：未因本设计重新运行。
- 服务器部署：未执行。
- HTTP 测试候选：`NO-GO`，仍等待后续功能、部署覆盖层和服务器验证。
- 生产发布：`NO-GO`，HTTPS、外部签收和生产证据仍缺失。
