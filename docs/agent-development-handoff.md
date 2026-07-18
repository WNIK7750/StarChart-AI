# Agent 开发交接

更新时间：2026-07-15

## 1. 交接结论

非 Agent 地基已经完成并归档，Agent 可以进入专项开发。当前不是空项目：仓库中已有一个可运行、可关闭、无模型也能工作的确定性 Agent 纵切。后续应在它的稳定契约上增加真实模型能力，不应推倒重写 Learning、Tools、Users 或现有工作流保存链路。

本轮交接只启动规划，不代表模型 Provider、会话、流式输出或长期记忆已经实现。后续执行顺序以 `docs/agent-delivery-roadmap.md` 为准。

## 2. 开始工作前的阅读顺序

1. `docs/pre-agent-foundation-final-report.md`：非 Agent 地基和已知限制。
2. `docs/agent-development-handoff.md`：当前事实、边界和修改入口。
3. `docs/agent-delivery-roadmap.md`：从最小闭环到发布收口的任务顺序。
4. `docs/agent-service-implementation.md`：现有确定性 Agent 的实施事实。
5. `docs/modular-monolith-guidelines.md`：模块化单体和抽象阈值。
6. `docs/agent-design.md`：产品愿景与候选能力，不作为当前实现事实源。

发生冲突时，优先级为：当前代码与测试 > 本交接和执行路线 > 实施记录 > 早期设计愿景。

## 3. 当前可运行基线

### 3.1 已有能力

- `POST /api/v1/agent/chat`：需要 `agent:chat` 权限，返回稳定结构化响应。
- 支持 QA、站内导航、工具推荐、学习计划和工作流生成五类意图。
- Agent 通过薄适配器读取 Learning、Tools 和 Users Context，不直接查询这些模块的数据表。
- 响应包含回答、卡片、引用、工具调用记录、步骤、工作流草案、追问和元数据。
- 输出守卫会移除不在站内白名单中的链接和悬空引用。
- 无模型时使用确定性检索和规则结果，`meta.mode=deterministic`、`readOnly=true`。
- `POST /api/v1/agent/workflows/save` 已形成真实写入闭环：显式确认、登录授权、幂等键、Users Assets facade 和审计。
- `frontend/assistant.html` 是真实入口，`assistant-page.js` 是页面业务脚本。

### 3.2 尚未实现

- 可替换模型 Provider 与真实生成式回答。
- SSE 流式传输、取消和断线处理。
- Agent 会话与消息持久化。
- 经过用户同意的长期记忆和上下文压缩。
- 完整评估集、模型质量基线、成本和 trace 观测。
- Firefox、WebKit 和真实移动设备上的 Agent 关键流程验收。

多 Agent、LangGraph、向量库和自动外部工具执行不是默认待办。只有达到本文件第 7 节的触发条件后才重新评估。

## 4. 稳定所有权和依赖方向

```text
Agent HTTP router
  -> Agent application/orchestration
      -> Model Provider boundary
      -> Learning read adapter -> Learning public service
      -> Tools read adapter    -> Tools public service
      -> Users Context facade  -> Users public read facade
      -> Users command facade  -> confirmed/idempotent/audited writes
      -> Output validator
```

- Agent 拥有：对话用例、提示、模型调用、工具选择、上下文预算、引用组装和输出验证。
- Learning 拥有：节点、路线、资料、章节、语义关系和学习规则。
- Tools 拥有：工具事实、分类、搜索、工作流候选和链接状态。
- Users 拥有：身份、权限、偏好、学习状态、用户资产、隐私同意和审计。
- Platform 拥有：配置、数据库迁移、错误格式、request ID、健康检查和部署运行时。

禁止 Agent 直接写业务表、复制领域 SQL、解析页面 DOM 获取事实，或把模型 SDK 对象传入其他领域模块。

## 5. 修改入口

| 需求 | 首要修改位置 | 必须保持的边界 |
| --- | --- | --- |
| 请求/响应字段 | `backend/app/agent/schemas.py` | 契约采用加法演进；破坏性变化升 contractVersion |
| 意图与编排 | `backend/app/agent/service.py`、`router.py` | 不在 HTTP router 或工具适配器复制规则 |
| 模型接入 | Agent 模块内新增 Provider 边界 | SDK 类型、重试和密钥不越过 Agent/Platform 边界 |
| Learning 工具 | `backend/app/agent/tools/learning_tools.py` | 只调用 Learning 公开 service |
| Tools 工具 | `backend/app/agent/tools/catalog_tools.py` | 只调用 Tools 公开 service |
| 用户上下文 | Users Context/Preferences facade | 最小必要投影，遵守隐私同意 |
| 用户写入 | 对应 Users command facade | 显式确认、授权、幂等、审计和事务 |
| 输出安全 | `backend/app/agent/evaluator.py` | 引用必须可追溯，链接必须来自允许来源 |
| Agent 页面 | `frontend/assistant.html`、`assets/js/assistant-page.js`、`assets/css/assistant.css` | API 返回为事实源；安全文本渲染；唯一渲染所有者 |
| 回归验证 | `tests/test_agent_services.py`、`tests/test_agent_frontend.mjs`、`scripts/verify-agent.ps1` | 每个新增能力同时增加契约、安全和失败路径证据 |

## 6. 面向修改的设计规则

### 6.1 保留确定性核心

确定性检索不是临时代码，而是测试 oracle、离线回退和模型输出校验依据。真实模型可以解释和组织事实，但不能替换引用、链接、工具身份、计划顺序合法性等可验证字段的来源。

### 6.2 只在真实外部边界增加接口

模型 Provider 是明确的外部边界，可以定义窄接口。SQLite 只有一个实现时不为每张 Agent 表创建 port/adapter 目录；会话持久化出现第二实现或复杂事务前，保持 Agent 模块内的 service/repository 结构。

Provider 应返回项目自己的标准结果，不向上泄漏供应商响应对象。切换 Provider 时，API schema、领域工具和前端不需要修改。

### 6.3 编排与传输分离

Agent 用例先产出完整的标准事件或结果；普通 JSON 和 SSE 只是两种传输方式。不要维护一套非流式业务逻辑和另一套流式业务逻辑。

### 6.4 Prompt 可版本化但不成为业务规则仓库

Prompt 可以独立文件化并记录版本，但权限、链接白名单、工具存在性、先修合法性、幂等和审计必须由代码执行。Prompt 变更需要评估集验证，不直接改写公共 API 契约。

### 6.5 能力通过组合根装配

Provider、工具集合、会话存储和 Feature Flag 在 Agent 组合根装配。测试可注入 fake provider；业务函数不读取全局供应商单例。Provider 不可用时可明确回退 deterministic，不能静默伪装为模型回答。

### 6.6 数据演进保持追加式

需要会话、消息、反馈或记忆表时使用新的编号迁移。不得修改已经应用的 001-015 迁移。会话数据和用户资产要有清晰删除、导出和保留策略。

## 7. 复杂度升级触发条件

只有出现对应事实时才升级：

| 候选能力 | 触发条件 |
| --- | --- |
| 第二 Provider | 已有真实切换、降级或成本路由需求 |
| LangGraph/状态图 | 一个请求存在可恢复长任务、多个持久化节点或人工中断后续跑 |
| 向量检索 | 关键词/结构化检索在评估集上无法达到目标，且有稳定语料和重建流程 |
| 长期记忆 | 用户明确开启同意，产品场景证明跨会话记忆有价值，并完成删除/导出 |
| 多 Agent | 单编排器在可观测评估中出现明确职责冲突，拆分能带来可测质量提升 |
| 队列/后台任务 | 请求生命周期无法承载真实长任务，并且需要重试、恢复或调度 |

这些能力仍留在同一部署单元，除非项目规模和部署需求发生实质变化。

## 8. 首个开发任务的起点

下一位执行者应从路线图 Phase 1 开始：在不改变现有 HTTP 响应结构的前提下，引入一个可注入的模型 Provider 边界，让真实模型只基于已检索的站内证据生成回答；失败、超时、未配置和校验不通过时回退确定性结果。

第一批代码不包含会话表、长期记忆、LangGraph、多 Agent 或全站悬浮入口。

开始编码前执行：

```powershell
.\scripts\verify-foundation.ps1
.\scripts\verify-agent.ps1
```

## 9. 每轮交接要求

每个阶段结束时更新 `docs/agent-delivery-roadmap.md`，并记录：

- 完成的用户可见闭环，而不是新增了多少抽象。
- 修改的公共契约、迁移和 Feature Flag。
- 实际执行的测试、浏览器环境和结果。
- 未覆盖风险、回滚方式和下一项未完成任务。
- 如果选择了新框架或存储，写明触发证据及替代方案。

