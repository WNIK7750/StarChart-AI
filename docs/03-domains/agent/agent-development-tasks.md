# Agent 开发任务书：全量路线与阶段 1

更新时间：2026-07-25

本文把 `agent-development-handoff.md` 的边界转成可执行任务。它不替代当前代码、测试或交接文档；发生冲突时，以当前代码和测试为准。

## 1. 已核对的起点

- `POST /api/v1/agent/chat` 已是一个受权限保护的、只读的确定性纵切：站内 Learning/Tools 检索、最小 Users Context、卡片/引用/步骤组装和输出守卫均已存在。
- 工作流保存是独立的已确认 Users Command；阶段 1 不得改变或复用它来写入任何 Agent 状态。
- `AgentStructuredResponse` 是现有前端的稳定响应形状；阶段 1 只能作兼容性扩展，不能移除或重命名字段。
- 当前专项测试覆盖五条确定性服务路径和一条前端契约路径，但尚不覆盖 Provider、配置、超时、取消、回退、提示注入或真实 HTTP 边界。
- 本任务书的基线验证于 2026-07-19 通过：`scripts/verify-agent.ps1` 与 `scripts/verify-foundation.ps1`。

## 2. 工程方法与不可变约束

采用“先简单、后证据、再扩展”的单 Agent 方法：先让一个受控的 Provider 在既有检索结果上组织回答，先用评估用例定义成功，再根据结果决定是否增加流式、会话、第二 Provider 或更复杂编排。不要因为可用框架而预先引入状态图、向量库或多 Agent。

| 规则 | 本项目落实方式 |
| --- | --- |
| 事实与生成分离 | Learning/Tools/Users 继续产生事实；模型只能生成自然语言回答，不能生成或修改业务事实、链接、引用身份和写命令。 |
| 最小可替换边界 | Provider 返回项目自有 DTO，不向 service、router、前端泄漏 SDK/供应商对象。组合根装配 Provider，测试注入 fake。 |
| 证据先于回答 | 每个 Provider 请求带受长度限制、带稳定 `citationId` 的站内证据包；响应中的卡片、引用、步骤仍由确定性代码组装。 |
| 防御纵深 | 输入限长、提示隔离、Provider 配置校验、超时/取消、响应解析、输出守卫、权限和回退各自独立生效。 |
| 评估驱动 | 先冻结阶段用例和可机器判定的断言，再实现能力；每个缺陷用例进入回归集。 |
| 可关闭与可解释 | Provider 默认关闭；任何未配置、失败、超时、取消或验证失败都可回到确定性结果，并在响应元数据和日志中说明原因。 |

方法论参考：Anthropic 对 Agent 的建议是从简单、可组合的模式开始，只在评估证明收益时增加复杂度；其工具与评估实践强调清晰工具契约、真实任务驱动的评估以及多层检查。参见 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)、[Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents) 和 [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)。

### 2.1 永久禁止项

- Agent 不直接访问领域表、不复制 Learning/Tools/Users SQL、不解析页面 DOM 作为事实源。
- 模型输出不得直接成为 Users Command、数据库写入、外链、引用、工具 ID、权限判断或审计记录。
- 不在阶段 1 创建会话/消息/记忆表，不实现 SSE，不引入 LangGraph、向量库、后台队列或多 Agent。
- 不在日志、异常、响应、测试快照或前端中暴露 API Key、Authorization 头、原始 Provider body 或不必要的用户数据。
- 网页只展示完成当前任务所需的信息、操作状态、错误恢复和必要用户引导；工程实现说明、内部模型/Provider 状态、装饰性重复文案或其它无关文字不得进入用户界面。

### 2.2 适度解耦：按需调用基线能力，不拆微服务

Agent 可以按用户任务调用现有基线能力，但不能获得一个可任意请求站内 URL 的通用 HTTP 工具。每项可调用能力必须有名称、输入 DTO、输出 DTO、权限/数据范围、调用预算和测试；初始允许集是 `learning.search`、`learning.get_context`、`learning.recommend_next`、`tools.search`、`tools.workflow`、`navigation.read` 与最小化的 `users.context`。新增能力先注册，再用评估证明有价值。

当前仓库是模块化单体，因此 Agent adapter 在同一进程内应调用 Learning、Tools、Users 的公开 service/facade，复用与现有 API 相同的 DTO 和语义，而不是为自己发送 loopback HTTP 请求。这样没有网络、认证转发和故障开销，也不会复制领域逻辑。若某能力将来被独立部署，才在 adapter 后以同一契约替换为 HTTP client；Agent 编排、Provider、前端和测试无需感知部署变化。

调用选择也应保持渐进：阶段 1 由确定性检索计划按意图和页面上下文选择零到少量只读能力，Provider 只组织得到的证据；不在阶段 1 允许模型自由循环、任意选 API 或自动执行写操作。模型驱动的工具选择只有在阶段 4 的评估证明固定计划不足时才作为单独任务引入。

## 3. 全量开发路线

### 阶段 0：基线冻结（已完成，本轮复核通过）

1. 运行 Agent 专项与非 Agent Foundation 门禁。
2. 记录现有确定性行为、未实现范围和回退基线。
3. 为新增阶段任务创建本文件；不修改已完成阶段的历史结论。

退出条件：两套门禁通过，普通首页、学习、工具和用户空间不依赖 Agent 可用性。

### 阶段 1：真实模型只读闭环

目标：在“站内检索 -> 模型组织回答 -> 输出校验”的单一流程中接入一个可替换的真实 Provider；失败时继续返回确定性结果。

工作包、接口和验收见第 4 节。正常顺序要求阶段 1 发布门槛完成后进入阶段 2；2026-07-23 用户明确将真实 Provider 上线验证延后，因此允许先推进默认关闭的阶段 2 开发切片，但生产发布仍不得绕过阶段 1 门槛。

### 阶段 2：SSE 与短期会话

1. [x] 让 JSON 与 SSE 复用同一个编排结果/事件模型，而非两套业务逻辑。
2. [x] 增加停止、超时、断线恢复、背压边界和前端增量渲染。
3. [x] 通过追加迁移保存最小会话和消息，覆盖用户隔离、分页、删除、到期清理和功能开关。
4. [x] 为流式和会话分别提供关闭开关；关闭后回到阶段 1 语义。

退出条件：流式和完整响应语义一致；取消后不继续写入；用户仅能访问自己的会话。

当前进度：已实现 `AI_NAV_AGENT_STREAM_ENABLED=0` 默认关闭的 SSE 传输，以及 `AI_NAV_AGENT_SESSIONS_ENABLED=0` 默认关闭的短期会话。支持增量协议的 Provider 可在累计前缀通过输出守卫后逐块发送；不支持的 Provider 继续从同一个最终响应安全投影。SSE 生产与网络消费之间使用默认 8、可配置 1 至 64 个事件的有界队列，慢客户端会暂停生产；连接或生成器关闭会取消 Provider。会话只有在客户端显式创建并携带 `sessionId` 时才写入，只保留用户问题和最终验证后的回答；默认 30 天、最多可配置 90 天，支持分页、用户删除和到期清理。

助手页已增加显式的“保存新会话”、会话列表、恢复、两步删除和移动端抽屉；不开启默认会话开关，不把匿名或无 `sessionId` 对话自动转为持久化。断线后不会自动再调用模型，只显示用户确认的“重新发送”；重试复用原问题、原会话和同一个 `X-Request-Id`。后端只在完整成功后将标准响应放入默认 300 秒、最多 512 项的进程内重放缓存；命中时不再次调用 Provider，相同请求标识携带不同内容返回 409，取消或失败请求不缓存。该缓存不跨 worker，阶段 1 生产仍保持单 API worker；多实例发布前再替换为共享幂等存储。真实 Provider 继续保持关闭，其 adapter 暂不声明增量能力。

运行观测已覆盖纯确定性请求、Provider 成功/回退、Token、成本、延迟、重放命中和请求标识冲突；管理员接口只返回无用户、无请求正文的进程内聚合。模型升级门禁已固定为脱敏配对评测：至少 20 组、无安全/引用失败、质量提升至少 0.05、成本与 P95 延迟均不超过基线 1.5 倍。门禁只产生人工评审建议，不修改路由；当前无真实配对数据，`qwen3.7-plus` 继续保持 0%。

运行拓扑保持单 FastAPI 部署单元、单 API worker 和 SQLite，不提前引入 Redis 或 Agent 微服务。`AI_NAV_API_WORKERS=1` 与 `AI_NAV_AGENT_RUNTIME_STATE_BACKEND=process_local` 是启动契约；配置多 worker 或未实现的共享后端会直接失败。只有单 worker 容量、滚动升级/故障切换或跨实例一致性出现可复核需求时，才在现有 adapter 后替换共享治理、重放和指标实现。

离线容量基线以单进程、并发 8 完成 64 次确定性请求，P95 为 262.02ms，通过 1500ms 开发门槛。该结果没有真实 Provider 网络延迟，标记为仅可同主机等级比较且不是生产容量承诺；最终上海服务器容量仍在上线阶段复核。

阶段 2 发布矩阵已将 Provider、Live、SSE、Sessions、重放、观测和单 worker 拓扑组合固化。`deterministic/fake + Live 1` 现在明确拒绝；管理员脱敏运行快照可区分 deterministic、fake、已配置但关闭、live 和无效配置，同时保持公开 `/agent/capabilities` 的最小契约不变。

2026-07-24 已完成 deterministic 阶段 2 端到端发布演练：临时数据库应用 18 个迁移，启用态与回滚态共 29/29 项检查通过。演练覆盖 readiness、管理员脱敏运行快照、SSE 完成事件、显式短期会话、浏览器断线后的同请求标识人工重试、消息幂等、会话删除，以及关闭 SSE/Sessions 后继续使用确定性 JSON 回答。真实 API Key 未加载、Provider 网络未调用；可复现脚本为 `scripts/rehearse-agent-stage2.py`，脱敏结果为 `docs/06-evidence/agent/agent_stage2_release_rehearsal.json`。

视觉约束（2026-07-23）：助手及后续 Agent 界面采用 Codex 启发的中性工作台方向——暖白主画布、雾灰侧栏、石墨主操作、低饱和边界和克制阴影；绿色仅表示运行状态。禁止默认使用蓝紫渐变、紫色焦点环、装饰性光斑或通用“插件卡片”风格。不得复制 Codex/ChatGPT 品牌标识与菜单结构。

### 阶段 3：经确认的用户闭环

1. [x] 完善既有工作流草案的预览、编辑、确认、冲突和重试体验。
2. 每轮只增加一种 Users Command（例如收藏或学习计划保存），由用户需求与风险评审决定。
3. 所有写入继续经过 Users facade、权限、幂等、事务和审计；模型只提出草案。
4. 长期记忆保持关闭，直到同意、导出、删除、保留期、质量验证和撤回行为均具备。

退出条件：模型无法自行写入；撤销、失败和重试不会产生重复或越权数据。

2026-07-24 已完成阶段 3 的第一个、也是本轮唯一的 Users Command 闭环。工作流草稿现在提供标题、说明和步骤的可编辑预览；保存前必须显式确认。首次提交后锁定草稿、请求体与幂等键，网络失败只允许“重试同一次保存”；完成响应重放会提示没有创建重复工作流。同一用户使用同一幂等键提交另一份语义不同的草稿时，后端返回 `409 WORKFLOW_IDEMPOTENCY_CONFLICT`，不再静默返回旧资产。真实浏览器演练在首次响应于服务端完成后人为中断，重试后数据库仍只有 1 条编辑后的工作流。脱敏结果见 `docs/06-evidence/agent/agent_stage3_workflow_save_rehearsal.json`。

2026-07-24 已补齐该 Users Command 的结果追踪，但没有增加新的写入命令。保存成功后，助手页提供携带 `workflowUid` 的个人工作流深链接；设置页加载用户范围列表后，仅对匹配项添加中性高亮、可访问标签和程序焦点。保存结果未知或发生 `WORKFLOW_IDEMPOTENCY_CONFLICT` 时，只提供不带目标 ID 的“核对个人工作流”入口。真实浏览器验证确认正常保存仅写入 1 次，成功导航不产生额外写入；冲突核对导航前后的写入计数不变。390px 视口无横向溢出。

2026-07-24 已完成工作流只读详情必要性审计。Users 列表契约已经返回完整有序步骤和工具可用性，因此不新增独立页面、路由或详情请求；设置页在现有条目内提供“查看步骤/收起步骤”的渐进展开。助手深链接命中的目标默认展开并获得焦点，普通条目默认折叠；失效工具仅显示状态文本，内部链接继续经过 URL 安全策略。真实浏览器验证覆盖桌面与 390px 移动端、手动展开/收起、深链接自动展开、失效工具和恶意快照链接，界面操作产生 0 次写请求。脱敏结果见 `docs/06-evidence/agent/agent_stage3_workflow_detail_rehearsal.json`。

### 阶段 4：质量与运行治理

1. [x] 建立版本化评估集：任务、试次、代码/模型/人工评分器、阈值和失败归因。
2. [x] 为每次请求记录最小 trace：请求标识摘要、模式、Provider、模型、提示版本、证据数、工具、耗时、成本、回退与校验错误；日志脱敏。
3. [x] 将安全、注入、越权、空结果、Provider 故障和回退纳入 CI；真实 Provider 测试保持显式、受限、非默认。
4. [x] 仅当评估证明收益，才评估第二 Provider、向量检索、状态图或多 Agent；当前均未启用，确定性关闭路径保持有效。

退出条件：本地与 CI 可重复运行评估；安全/越权零放行；每个复杂组件均可关闭并回退。

### 阶段 5：体验与发布收口

1. [x] 补全会话、停止、重试、引用、确认、错误恢复、键盘、焦点、读屏、长文本、窄屏和 reduced motion 体验。
2. [x] 覆盖 Chromium、Firefox、WebKit、Opera 与至少一种真实移动设备。
3. [x] 执行 Agent、Foundation、迁移、备份恢复、安全、性能和链接等全部离线门禁。
4. [x] 发布说明必须包含功能开关、已知限制、Provider 数据边界、成本阈值、监控、回滚与故障演练记录。
5. [ ] 【上线前处理】在生产配置注入后复核密钥、CORS、Cookie、限流、日志脱敏、功能开关和真实 Provider 回滚门禁。

退出条件：Provider 故障或 Agent 关闭时网站其他功能不受影响，且发布可复现、可回滚。

2026-07-24 首个阶段 5 体验缺口已修复：移动端“会话”按钮现在控制真实存在的 `contextPanel`，抽屉打开后焦点进入“关闭”，Esc 或关闭按钮会收起抽屉并把焦点归还触发按钮。Chromium、Firefox、WebKit 与本机 Opera 在 390×844、reduced motion 环境下通过，页面宽度 390/390、4000 字符长文本无溢出、控制台错误为 0；Pixel 7 与 iPhone 15 官方设备仿真同样通过。真实移动设备和读屏发布验收仍待完成。该切片没有新增网页说明文字。

请求状态现使用 polite、atomic 的 `role=status` live region；停止按钮声明 Esc 快捷键。浏览器模拟未完成请求时，Esc 能取消请求、隐藏停止按钮、宣布“已停止”并把焦点返回输入框。该项只增加辅助技术语义，不增加可见文案。

2026-07-25 对话页已按传统生成式 AI 工作区重构：桌面端采用固定短期会话侧栏、开放式回答阅读流、右对齐用户气泡、回答内联来源与底部输入器；移动端采用单栏内容和带遮罩的会话抽屉。视觉继续使用 Codex 式中性灰黑体系，没有引入 DeepSeek 品牌蓝、蓝紫渐变、营销区或无关说明。Chromium 与 WebKit 在 1440×900、390×844 下通过真实回答渲染、来源、会话列表、抽屉焦点/Esc、零横向溢出和零控制台错误检查。Firefox 通过原生无头模式补齐 1440×900 与 390×844 渲染证据，绕过 Playwright 1.61.1 `_page` 驱动错误；页面无可见溢出或错位。Opera Connector 已在用户启用全部可见授权后取得真实 Opera 桌面截图并复核完整无障碍树，页面主体、顶栏、侧栏和输入区无可见裁切、重叠、横向溢出或框架错误覆盖层。连接器本身不提供点击和控制台接口，因此交互与控制台契约继续由 Chromium/WebKit 自动化覆盖，不将其描述为 Opera 原生点击证据。新布局实机与读屏验收继续保留为阶段 5 待办。

发布收口文档已完成，见 `docs/04-operations/agent/agent-stage5-release-runbook.md`。功能开关、已知限制、Provider 数据边界、并发/成本阈值、监控、发布门禁、回滚顺序和故障演练证据均有固定入口；机器可读进度见 `docs/06-evidence/agent/agent_stage5_experience_audit.json`。完整 Agent 门禁现为 91 项 Python 与 3 项 Node/SSE 通过，未读取真实 `.env`、未调用 Provider。

完整 Foundation 门禁随后再次通过：前端 25 项、Tools 6 项、Learning 19 项 Python 与 2 项 Node、Users 43 项，以及迁移 20、备份恢复、安全、性能和链接检查均通过。

2026-07-25 真实手机通过临时 Quick Tunnel 完成验收：用户提供的实机截图与结果确认竖屏、横屏、会话抽屉、长文本、reduced motion、遮挡和横向溢出均无问题，审计只记录内容无关结论，不保存设备标识。验收时发现隔离服务器虽然声明会话可用，却未实现 `POST /agent/sessions`，聊天接口也固定返回失败，导致“新建对话”出现 `Not found`；现已补齐纯内存的创建、列表、历史、删除和确定性模拟回答，并新增端到端契约测试。390×844 公网自动化复测确认新建会话、模拟回复和侧栏记录可用，页面宽度 390/390、框架错误层为 0、控制台错误为 0。正式 Agent API、认证、数据库和 Provider 未改变。

2026-07-25 Windows Narrator 人工验收通过：输入框名称、检索状态、Esc 停止状态与焦点归还均正常，没有报告重复或漏读。Quick Tunnel 与隔离服务器已立即关闭，阶段 5 体验审计状态更新为 `complete_offline`。真实 Provider 合规、上海服务器出站白名单、生产配置与容量验证仍保留为最终上线任务。

2026-07-25 短期会话管理已完成：同一用户存在尚未完成首轮问答的空会话时，不再允许连续创建；完成一次问答后重新开放“新建对话”。短期会话继续保存在用户隔离、默认 30 天到期的服务端缓存中。用户可修改显示标题、置顶或取消置顶多个会话；后置顶的排在前置顶的更前面。桌面端与 390×844 移动端完成创建约束、两轮对话、连续置顶、取消置顶、改标题、抽屉布局、零横向溢出和零控制台错误复测。

2026-07-25 长期对话方案已确认并实现：每个用户最多拥有三个长期对话；升级在同一数据库事务内复制消息并删除短期记录，失败则完整保留短期会话。升级以来源短期会话 ID 幂等，重试不会重复占用名额。长期对话位于短期会话上方，可继续提问，并复用改标题、置顶、取消置顶和删除能力。完整方案见 `docs/02-architecture/decisions/agent-long-conversation-storage-proposal.md`。

2026-07-25 Agent 对话隐私生命周期已补齐：需要当前密码的用户数据导出现在包含该用户的短期与长期对话及可见消息，同时排除内部请求幂等标识、长期来源短期会话标识、Provider 原始载荷、系统提示与推理过程。注销软删除及 30 天恢复期继续保留对话；仅在恢复期结束后的最终匿名化中级联删除该用户的两类对话，其他用户不受影响。Users 完整门禁 43 项 Python、前端、安全、20 个迁移、备份恢复与性能检查通过。

下一项：真实 Provider 合规、上海出站白名单、生产配置和容量验证继续保留到最终上线；在未获得上线授权前不读取真实 `.env`、不加载 API Key、不发起真实模型请求。

2026-07-25 开发完成审计：当前权威任务书中的未勾选项均已明确标记为“上线前处理”。长期记忆、跨进程运行状态、第二 Provider、向量检索、状态图和多 Agent 均为评测或规模阈值触发的可选扩展，不是当前版本的未完成开发任务。机器可读结论见 `docs/06-evidence/agent/agent_development_completion_audit.json`，并由 Agent 门禁检查不得重新出现未标注的离线待办。

## 4. 阶段 1：开发任务包

### 4.1 Definition of Ready

发出首个真实 Provider 请求或启用真实流量前必须确认：

- [x] 已选择阿里云百炼华北 2（北京）与 `qwen3.5-flash`，并在 `docs/02-architecture/decisions/adr-agent-provider-cn.md` 记录决策；`qwen3.7-plus` 升级比例保持 `0`，DeepSeek 延后到阶段 2。
- [x] 已确认并实现每用户/全局并发、有限排队及应用内单请求/日/月成本上限。
- [ ] 【上线前处理】按 `docs/04-operations/agent/agent-provider-stage1-release-checklist.md` 使用默认业务空间完成专属域名、上海服务器出站 IP 白名单、供应商侧费用限制与受控真实验证；当前真实流量保持关闭。
- [x] 固定向第三方 Provider 发送的最小数据集：当前用户问题与站内公开证据包；不发送工作流资产明细、身份资料、令牌或长期记忆。
- [x] 在 `2026-07-20` 隐私政策与 Agent 输入区完成第三方模型处理告知，并在 Provider 调用前检查当前版本 `privacy_policy` 同意；`agent_memory` 继续独立授权。
- [ ] 【上线前处理】核对并归档供应商数据处理协议，确认不用于训练和约定留存策略后才开启生产实时调用。
- [x] 已准备可撤销的专用 API Key 环境变量链路；真实 Key 仅存在于 Git 忽略的本地 `.env` 或部署密钥管理中。
- [x] 本阶段已运行 Agent、Users 和相关前端回归；39 项 Agent、42 项 Users、30 条评估样例及前端契约通过。
- [ ] 【上线前处理】真实 Provider 受控验证完成后再次运行完整 `scripts/verify-foundation.ps1`，确认没有无关回归。

### 4.2 WP1：自有 Provider 契约与错误模型

建议新增 `backend/app/agent/providers/`，保持依赖单向：`service/orchestrator -> provider protocol -> provider implementation`。目录名不是完成标准；下列行为才是标准。

1. 定义项目 DTO：
   - `ProviderRequest`：`requestId`、`promptVersion`、受限系统指令、用户问题、`EvidenceItem[]`、取消/截止时间上下文。
   - `EvidenceItem`：稳定 `citationId`、标题、摘要、站内 `href`、来源类型；不得包含 Provider SDK 对象或原始数据库行。
   - `ProviderResult`：仅允许模型组织出的 `answer`（可选、受长度限制的澄清问题）；禁止携带链接、工具调用、业务命令或任意 JSON。
   - `ProviderFailure`：稳定的 `kind`（`not_configured`、`cancelled`、`timeout`、`authentication`、`rate_limited`、`unavailable`、`invalid_output`），可安全展示的摘要，以及可记录的 HTTP/供应商分类，不含密钥或原始 body。
2. 定义窄异步 Protocol，例如 `generate(request) -> ProviderResult`；调用者不依赖任意供应商 SDK 类型。
3. 实现 `FakeProvider`，可按用例返回成功、各类失败、超时或无效输出。所有单元测试默认只使用 fake。
4. 实现一个真实 Provider adapter。HTTP 客户端、供应商请求格式、密钥和重试都只留在此 adapter 内；对外只返回项目 DTO。

验收：可用 fake 完整驱动成功/失败路径；替换真实 Provider 不需要修改 Agent API、Learning、Tools、Users 或前端。

### 4.3 WP2：配置、组合根与功能开关

1. 在 `backend/app/core/config.py` 增加显式 Agent 配置（名称以实现时的项目约定为准）：Provider 类型、启用开关、模型、请求超时、最大重试数、最大输出长度和 API Key 环境变量名。
2. 启用真实 Provider 时校验必填项；未配置或非法配置不可静默当作真实模式运行。默认 `deterministic`，生产环境不接受开发假 Provider。
3. 在 Agent 组合根/factory 选择 deterministic、fake 或真实 Provider；路由只注入编排服务，不读取环境变量、不持有 SDK client。
4. 规定运行时开关语义：关闭 Provider 后，新请求立即走确定性路径；已开始的请求遵循其创建时的取消/超时规则；阶段 1 没有持久状态可迁移。
5. 请求日志只记录 Provider 名称、模型别名、模式、耗时、重试次数和稳定错误类别；增加密钥清洗测试。

验收：未配置、关闭、非法配置和真实 Provider 故障均返回 HTTP 200 的确定性响应，且 `meta` 明确说明模式与安全的回退原因；无需重启数据库或修改领域数据。

### 4.4 WP3：只读编排与兼容响应

1. 将 `draft_agent_response` 拆成可测试的步骤：
   - 一个有调用预算的确定性基线能力计划：按意图和页面上下文调用零到少量 Learning、Tools、Navigation、Users 公开 adapter，而不是每次无条件调用所有能力；
   - 现有确定性卡片/引用/步骤/工作流草案；
   - 构造受预算限制的证据包；
   - 调用 Provider（若启用）；
   - 校验 Provider 自然语言；
   - 用确定性结构组装 `AgentStructuredResponse`；
   - 运行既有最终输出守卫。
2. 模型只替换 `answer`，最多补充受控澄清问题；卡片、引用、步骤、`workflowDraft`、`toolCalls` 及 `readOnly=true` 必须由确定性逻辑继续产生。
3. 保持 `AgentStructuredResponse` 的已有字段和语义。`toolCalls` 继续由能力计划记录实际调用/跳过状态；仅向 `meta` 加可选兼容字段，例如 `mode: deterministic|provider`、`provider`、`fallbackReason`、`promptVersion`；原 deterministic 响应维持原值。必要时用 OpenAPI/JSON 快照证明兼容。
4. Prompt 放在版本化的 Agent 模块资源中，但提示不承担授权、链接白名单、引用存在性、幂等或审计等业务规则。证据和用户文本使用明确分隔符并标记为不可信内容；任何“忽略规则/调用工具/泄漏提示”的文本都不能改变系统规则。
5. 设定总截止时间、单次请求超时和至多一次仅针对瞬时失败的重试；取消、配置/认证错误、输入错误和无效输出均不重试。客户端断开时取消在途 Provider 请求，不产生写入。

验收：Provider 成功时，回答仅根据传入证据组织，所有卡片/引用仍可追溯到站内事实；每项基线能力均可证明只按需调用且没有 HTTP 回环或领域 SQL；失败时，回答与现有确定性行为等价，且客户端能区分 `provider` 与 `deterministic` 回退。

### 4.5 WP4：输出、隐私与安全守卫

1. 扩展 `evaluator.py` 或其专用子模块，验证 Provider 文本：非空、字符/段落预算、可显示文本、无模型生成的站外 URL、无伪造引用 ID、无写入指令注入响应结构。
2. 保留现有站内 href 白名单与悬空引用清理；增加“模型文本包含外链或伪造引用时仍不会形成可点击事实”的测试。
3. 传递给 Provider 前执行最小化和红线检查：不发送用户身份、令牌、完整资产列表、审计数据、长期记忆或未授权私有内容。Users Context 只使用既有 facade 的允许投影。
4. 增加限制：输入最大长度、证据条数/每项长度/总 token 预算、输出长度、最大总尝试数和每请求成本预算（阶段 1 可先配置为保护阈值而非完整计费）。
5. 在前端仅展示 API 的文本字段；不把 Provider HTML/Markdown 当作可信 DOM。现有 `textContent` 渲染策略保持不变。

验收：提示注入、恶意站内内容、Provider 回显密钥样式文本、外链、伪造引用、过长输入/输出和越权上下文均被阻断或安全回退。

### 4.6 WP5：评估、测试与受控真实验证

先创建一个小型、版本化的阶段 1 用例集（建议 20--30 条），覆盖 QA、导航、工具推荐、学习计划、工作流建议、空结果、中文偏好、免费优先、拒绝越权写入、提示注入、恶意证据、Provider 失败和用户取消。每例记录输入、最小证据条件、预期模式、允许/禁止 citation ID、预期工具调用和安全断言；不要把模型自由文本做成脆弱的完全相等断言。

| 层级 | 必测内容 | 默认执行环境 |
| --- | --- | --- |
| 单元 | DTO、配置校验、fake、错误映射、重试、截止时间、取消、证据预算、文本验证 | 无网络、fake |
| 服务 | Provider 成功、未配置、超时、限流、无效输出和回退；已有确定性行为不回归 | 无网络、fake |
| HTTP/契约 | 鉴权、422、稳定 `AgentStructuredResponse`、新增 meta 向后兼容、不会泄密 | TestClient、fake |
| 前端 | `provider`/回退状态、取消前的禁用/恢复、文本安全渲染、现有工作流保存不受影响 | Node/浏览器测试 |
| 受控真实 Provider | 一条只读 QA、一条空结果、一条故障注入或禁用验证；记录模型/时间/成本上限，不进默认 CI | 显式开关与临时凭据 |

更新 `scripts/verify-agent.ps1`，使其执行全部 fake/契约/安全测试；真实 Provider 验证必须是单独脚本或显式 `-RealProvider` 参数，默认禁用且不会在 CI 或无凭据环境联网。

阶段 1 发布门槛：所有默认 Agent 与 Foundation 门禁通过；阶段 1 用例集的所有代码型安全/引用/回退断言通过；受控真实验证通过并留下脱敏证据；任何 Provider 失败均不降低非 Agent 页面可用性。

## 5. 实施顺序、交付物与回滚

1. 先完成第 4.1 的授权与 ADR，再冻结第 4.6 用例集。
2. 依次完成 WP1、WP2、WP3、WP4；每个工作包均用 fake 测试通过后再进入下一个。
3. 完成 WP5 的默认门禁，最后才执行一次受控真实 Provider 验证。
4. 更新 `docs/03-domains/agent/agent-development-handoff.md` 末尾的阶段记录，内容只描述已交付的用户闭环、契约、验证、开关、风险和下一任务；不得把新增目录本身写成完成。

回滚：将 Provider 启用开关关闭或 Provider 选择设为 `deterministic`，保留所有确定性检索和输出守卫。阶段 1 不新增迁移和持久状态，因此不需要数据回滚。若真实 Provider 输出质量、成本或安全断言不达标，停止启用真实模式，保留失败用例并回到 fake/确定性修复循环。

## 6. 阶段 1 完成定义

- 一个真实 Provider 能在明确启用后只基于站内证据生成回答；Provider SDK/HTTP 细节不越过 Agent 边界。
- 现有响应、确定性能力、引用、工作流草案和 Users 写入链路保持兼容。
- 未配置、关闭、取消、超时、限流、认证失败、不可用和无效输出均有稳定分类、无密钥泄露的可观测记录以及确定性回退。
- fake、服务、HTTP/契约、前端、安全/注入与受控真实 Provider 验证均有证据；默认 CI 不依赖真实密钥或网络。
- 未创建会话、记忆或 SSE；未引入多 Agent、向量库、状态图或直接写入能力。

未满足以上任一项时，阶段 1 仍是进行中，下一项工作应优先修复失败用例而不是启动阶段 2。

## 7. 当前实施状态（2026-07-23）

阶段 1 第一批代码已经落地，但阶段 1 尚未完成，也未授权真实流量：

- 已实现项目自有 Provider DTO/Protocol、离线 fake 和 OpenAI-compatible Chat Completions adapter。
- 已实现组合入口、独立真实流量熔断开关与局部配置降级；默认 `deterministic`，Provider 误配置不会阻止普通网站启动。
- 已实现按意图和纯指代页面上下文选择 Learning、Tools、Navigation 与最小 Users Context 基线能力；同进程调用公开 service/facade，不走 HTTP 回环，不复制领域 SQL。
- 模型只能替换自然语言 `answer`；卡片、引用、工具调用和工作流草案继续由确定性代码产生。
- 已实现 8 秒 Provider 调用截止时间、最多一次瞬时重试、客户端断连与 ASGI 父任务取消向 HTTP transport 传播、输入秘密阻断、响应体与证据预算、输出守卫、稳定回退原因、安全 request ID 和脱敏运行日志；断连监听不会在成功路径取消 Starlette 的 receive，避免与现有中间件形成响应死锁。
- Agent 专项门禁现覆盖 73 项 Python 测试方法、30 条版本化阶段 1 评估样例、真实 ASGI 的 JSON/SSE、管理员指标与运行快照授权、200/401/409/422/503 契约、无内容运行指标、模型升级门禁、单 worker 拓扑保护、前端契约和语法检查；Foundation 门禁已通过。

本地模式：

```powershell
# 默认，不调用外部模型
$env:AI_NAV_AGENT_PROVIDER="deterministic"

# 仅用于本地验证 Provider 编排，不联网
$env:AI_NAV_AGENT_PROVIDER="fake"
```

OpenAI-compatible adapter 的配置接口已经具备，但以下示例不能视为生产启用授权：

```powershell
$env:AI_NAV_AGENT_PROVIDER="openai_compatible"
$env:AI_NAV_AGENT_PROVIDER_BASE_URL="https://已批准的服务地址/v1"
$env:AI_NAV_AGENT_PROVIDER_MODEL="qwen3.5-flash"
$env:AI_NAV_AGENT_PROVIDER_UPGRADE_MODEL="qwen3.7-plus"
$env:AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO="0" # 评估批准前强制为 0
$env:AI_NAV_AGENT_PROVIDER_API_KEY="从运行时秘密管理注入"
$env:AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS="已批准的服务主机名"
$env:AI_NAV_AGENT_PROVIDER_LIVE_ENABLED="1" # 独立熔断开关；未授权前保持 0
$env:AI_NAV_AGENT_PROVIDER_TIMEOUT_SECONDS="8"
$env:AI_NAV_AGENT_PROVIDER_MAX_RETRIES="1"
$env:AI_NAV_AGENT_PROVIDER_MAX_INPUT_TOKENS="4000"
$env:AI_NAV_AGENT_PROVIDER_MAX_OUTPUT_TOKENS="600"
$env:AI_NAV_AGENT_PER_USER_CONCURRENCY="1"
$env:AI_NAV_AGENT_GLOBAL_CONCURRENCY="8"
$env:AI_NAV_AGENT_QUEUE_LIMIT="32"
$env:AI_NAV_AGENT_QUEUE_TIMEOUT_SECONDS="3"
$env:AI_NAV_AGENT_PER_REQUEST_COST_CNY="0.02"
$env:AI_NAV_AGENT_PER_USER_DAILY_COST_CNY="0.1"
$env:AI_NAV_AGENT_GLOBAL_DAILY_COST_CNY="5"
$env:AI_NAV_AGENT_GLOBAL_MONTHLY_COST_CNY="80"
```

Provider、默认模型、北京地域、最小数据告知/同意门槛及进程内并发/成本保护已经写入 ADR。真实 Provider 启用前仍需完成：供应商数据处理协议核对、账户余额硬上限与禁止自动充值、生产主机允许列表与密钥轮换方案，以及受控联网验证。进程内账本重启后清零，因此阶段 1 生产部署保持单 API worker；此前保持 `deterministic` 或 `fake`。

## 8. 阶段 4 当前实施状态（2026-07-24）

阶段 4 的首个最小质量治理切片已完成，目标是让同一套离线门禁在中文工作区、损坏或迁移后的虚拟环境以及 CI 中保持可复现，而不是新增服务或依赖真实 Provider：

- [x] 新增共享 `scripts/python-runtime.ps1`：依次解析显式 `AI_NAV_PYTHON`、可工作的项目虚拟环境、`.venv/pyvenv.cfg` 记录的原始解释器和 PATH Python；使用原始解释器时仅补入项目 `backend` 与现有虚拟环境包目录。
- [x] `verify-agent.ps1`、`verify-users.ps1`、`verify-tools.ps1`、`verify-learning.ps1` 已统一使用该解析器，不再各自维护易漂移的解释器回退。
- [x] Learning 门禁按明确文件名执行本地测试发现，避免第三方同名 `tests` 包遮蔽工作区测试。
- [x] Tools 迁移测试改为比较迁移目录与 `schema_migrations` 的精确文件集合，不再硬编码迁移数量；新增迁移时仍可发现漏跑、重复或未知迁移。
- [x] 已核对 CI：Windows + Python 3.12 创建有效项目虚拟环境，并顺序执行 Foundation 与 Agent 门禁；共享解析器在该路径优先使用项目虚拟环境，不改变 CI 的联网与密钥边界。
- [x] Agent 门禁通过：75 项 Python 测试、3 项 Node/SSE 测试、前端语法与 whitespace 检查。
- [x] Foundation 门禁通过：Frontend 25 项、Tools 6 项、Learning 19 项 Python + 2 项 Node、Users 43 项，以及内容链接、性能、命令安全、18 个迁移与备份恢复、Users 验收报告。
- [x] 30 条阶段 1 样例已生成 `agent-evaluation-manifest-v1` 脱敏清单：固定 20 条路由/能力用例、10 条 Provider 输出守卫用例、5 类意图与 6 类拒绝原因覆盖，并记录格式无关的语义 SHA-256。
- [x] `verify-agent.ps1` 已加入评估清单陈旧检查；样例内容、分类、期望或数量变化但未同步清单时，CI 以稳定失败分类阻止合入。
- [x] CI 路径过滤已覆盖 Agent 基线与运维文档，并在门禁通过后将脱敏评估清单归档为保留 14 天的构建制品，便于不同提交间下载比较。
- [x] 模型升级输出已拆分为稳定决策报告与可选运行归档元数据；UTC 时间和原始字节哈希不再污染可比较的决策主体。
- [x] 空白模型比较模板已固化 `KEEP_FLASH_0_PERCENT` CI 基线；清单或判定逻辑漂移但未同步基线时，以 `MODEL_DECISION_ARTIFACT_STALE` 阻止合入。
- [x] CI 构建制品同时归档阶段 1 评估清单与空白模型决策基线，二者均不包含问题、回答或用户数据。
- [x] 新增盲评分配与评分双文档契约：模型、成本和延迟只存在于运营侧分配文件，评分侧只提交匿名样本编号、五档任务分和安全/引用布尔结果。
- [x] 脱敏编译器强制唯一匿名样本、完整样本集合、同用例/试验双模型配对、至少 20 个不同用例、已批准模型与阶段 1 用例白名单。
- [x] 已提供空白模板和盲评执行手册；为平衡成本，一人完成初评，仅对安全/引用失败、边界分数或达到 5% 审查条件的样本启动第二人复核。
- [x] 盲评协议已生成 `agent-blind-protocol-manifest-v1` 内容无关清单，固定文档字段、评分档位、覆盖阈值、匿名编号格式、复核触发条件和 14 类稳定失败。
- [x] Agent 门禁以 `BLIND_EVAL_PROTOCOL_ARTIFACT_STALE` 检查协议代码与提交清单；CI 同时归档评估集、盲评协议和空白模型决策三份脱敏制品。
- [x] 每请求 trace 已补齐实际只读工具和独立校验错误字段；请求标识使用 SHA-256 前 24 位，字段白名单禁止问题、回答、用户身份或密钥进入日志。
- [x] 阶段 4 离线完成审计通过，证据见 `docs/06-evidence/agent/agent_stage4_completion_audit.json`；真实 Provider 合规与受控验证继续属于上线门禁。

该切片没有读取真实 `.env`、没有加载真实 API Key、没有发出 Provider 请求，也没有改变模块化单体与薄 Agent adapter 的架构边界。脱敏门禁证据见 `docs/06-evidence/agent/agent_stage4_foundation_gate_rehearsal.json`。

圆标视觉修复：工作流步骤序号现在使用组件级选择器覆盖通用列表 `span` 样式，固定双轴居中、零外边距和等宽数字。Chromium 实测 `1`、`2`、`10` 的最大水平中心偏差为 `0.008px`、垂直偏差为 `0px`，390px 视口无横向溢出。

下一项：进入阶段 5 体验与发布收口审计，先核对错误恢复、键盘/移动端体验、发布说明和回滚证据的剩余差距；上线前 Provider 合规与上海部署操作继续保持待办，不改变 `qwen3.7-plus` 的 `0%` 比例。
