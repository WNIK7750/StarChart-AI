# 数据、API、前端、部署与质量

## 1. 当前数据库事实

只读查询 `database/ai_nav.sqlite3` 得到：

| 内容 | 行数 |
| --- | ---: |
| `schema_migrations` | 22 |
| `navigation_items` | 4 |
| `difficulty_levels` | 6 |
| `knowledge_domains` | 5 |
| `roadmap_nodes` | 16 |
| `roadmap_edges` | 7 |
| `roadmap_domain_nodes` | 23 |
| `learning_resources` | 6 |
| `learning_materials` | 16 |
| `learning_material_sections` | 64 |
| `learning_node_tags` | 48 |
| `learning_node_links` | 88 |
| `tool_categories` | 9 |
| `tool_subcategories` | 37 |
| `ai_tools` | 144 |
| `tool_placements` | 138 |
| `tool_latest_slots` | 12 |
| `tool_workflows` | 3 |
| `workflow_tools` | 11 |

为保护本地开发数据，本次没有统计或展示用户、会话、审计等私有表的行数。

## 2. 46 张表的领域分组

### Platform 与内容

```text
app_settings
navigation_items
difficulty_levels
knowledge_domains
roadmap_nodes
roadmap_edges
roadmap_domain_nodes
learning_resources
learning_materials
learning_material_sections
learning_node_tags
learning_node_links
tool_categories
tool_subcategories
ai_tools
tool_placements
tool_latest_slots
tool_workflows
workflow_tools
```

### Users

```text
user_accounts
user_auth_passwords
user_auth_rate_limits
user_security_questions
user_profiles
user_preferences
user_sessions
user_verification_tokens
roles
permissions
role_permissions
user_role_assignments
user_login_logs
user_audit_logs
user_privacy_consent_events
user_data_requests
user_saved_workflows
user_saved_workflow_steps
user_learning_progress
user_learning_section_progress
user_learning_activity
user_favorites
```

### Agent

```text
agent_chat_sessions
agent_chat_messages
agent_long_conversations
agent_long_conversation_messages
```

### 迁移治理

```text
schema_migrations
```

## 3. API 地图

统一前缀：`/api/v1`

### 3.1 Common / Platform

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/navigation` | 主导航 |
| GET | `/runtime/public` | 公开部署能力 |
| GET | `/health/live` | 进程存活 |
| GET | `/health/ready` | 数据库与迁移就绪 |
| GET | `/health` | 兼容健康检查 |

### 3.2 Learning

| 方法 | 路径 |
| --- | --- |
| GET | `/learning/roadmap` |
| GET | `/learning/resources` |
| GET | `/learning/search` |
| GET | `/learning/agent-context` |
| GET | `/learning/nodes/{slug}` |
| GET | `/learning/nodes/{slug}/next` |
| GET | `/learning/nodes/{slug}/relations` |

### 3.3 Tools

| 方法 | 路径 |
| --- | --- |
| GET | `/tools/catalog` |
| GET | `/tools/categories` |
| GET | `/tools/search` |
| GET | `/tools/agent-context` |
| GET | `/tools` |
| GET | `/tools/latest` |
| GET | `/tools/workflows` |

### 3.4 Auth

| 方法 | 路径 |
| --- | --- |
| GET | `/auth/username-available` |
| POST | `/auth/register` |
| POST | `/auth/login` |
| POST | `/auth/refresh` |
| POST | `/auth/logout` |
| GET | `/auth/me` |
| POST | `/auth/password-reset/start` |
| POST | `/auth/password-reset/confirm` |

另有兼容/弃用的 security password reset 路径；其中 verify 固定返回 410，安全问题不能直接授权密码重置。

### 3.5 Users 账号与设置

| 方法 | 路径 |
| --- | --- |
| GET/PATCH | `/users/me/account` |
| PATCH | `/users/me/password` |
| GET/PUT | `/users/me/security-questions` |
| GET/PATCH | `/users/me/profile` |
| POST | `/users/me/avatar` |
| GET/PATCH | `/users/me/preferences` |
| GET | `/users/me/preferences/context` |
| GET | `/users/me/sessions` |
| POST | `/users/me/sessions/revoke-others` |
| DELETE | `/users/me/sessions/{session_uid}` |

### 3.6 Users 学习状态

| 方法 | 路径 |
| --- | --- |
| GET | `/users/me/learning/dashboard` |
| GET | `/users/me/learning/progress` |
| GET | `/users/me/learning/nodes/{node_slug}` |
| PUT | `/users/me/learning/nodes/{node_slug}/sections/{section_uid}` |
| PUT | `/users/me/learning/progress/{node_slug}` |
| POST | `/users/me/learning/activity` |
| POST | `/users/me/learning/import` |
| GET | `/users/me/learning/recent` |
| GET | `/users/me/learning/resume` |
| GET/POST | `/users/me/favorites` |
| DELETE | `/users/me/favorites/{favorite_uid}` |

### 3.7 Users Assets

| 方法 | 路径 |
| --- | --- |
| GET/POST | `/users/me/assets/workflows` |
| GET/PATCH | `/users/me/assets/workflows/{workflow_uid}` |
| POST | `/users/me/assets/workflows/{workflow_uid}/archive` |
| POST | `/users/me/assets/workflows/{workflow_uid}/restore` |
| GET | `/users/me/workflows` |

### 3.8 Privacy

| 方法 | 路径 |
| --- | --- |
| GET | `/users/me/privacy/consents` |
| PUT | `/users/me/privacy/consents/{consent_type}` |
| POST | `/users/me/privacy/export` |
| GET | `/users/me/privacy/deletion-requests/current` |
| POST | `/users/me/privacy/deletion-requests` |
| DELETE | `/users/me/privacy/deletion-requests/{request_uid}` |
| POST | `/users/privacy/deletion-requests/{uid}/execute` |
| POST | `/users/privacy/deletion-requests/{uid}/restore` |
| POST | `/users/privacy/deletion-requests/{uid}/anonymize` |

后三项要求管理权限。

### 3.9 Agent

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/agent/capabilities` | SSE/会话能力 |
| POST | `/agent/guest/chat` | 受开关控制的 deterministic 游客聊天 |
| POST | `/agent/chat` | 登录 JSON |
| POST | `/agent/chat/stream` | 登录 SSE |
| POST | `/agent/workflows/save` | 用户确认后保存工作流 |
| POST | `/agent/sessions` | 创建短期会话 |
| POST | `/agent/sessions/draft` | 复用或创建唯一空草稿 |
| GET | `/agent/sessions` | 分页列表 |
| GET/PATCH/DELETE | `/agent/sessions/{session_uid}` | 详情与管理 |
| POST | `/agent/sessions/{session_uid}/upgrade` | 原子升级长期对话 |
| GET | `/agent/long-conversations` | 长期列表 |
| GET/PATCH/DELETE | `/agent/long-conversations/{uid}` | 长期详情与管理 |
| GET | `/agent/operations/metrics` | 管理员聚合指标 |
| GET | `/agent/operations/runtime` | 管理员脱敏运行快照 |

## 4. 前端行为

### 4.1 API 层

前端 HTTP 适配器负责：

- API base path
- JSON 序列化
- 错误标准化
- Access Token 注入
- Refresh Cookie 刷新
- retry count
- AbortSignal
- `X-Request-Id`

### 4.2 Agent 模式选择

启动时：

1. 读取登录态；
2. 读取 `/runtime/public`；
3. 登录模式再读取 `/agent/capabilities`；
4. 登录用户可使用服务端 sessions；
5. 游客若允许 guest chat，则使用 localStorage 会话；
6. 流式能力不可用时使用 JSON；
7. SSE 已开始后发生错误，不自动重复发送。

### 4.3 SSE 客户端

`agent-sse.js` 只接受三类事件：

- `response.started`
- `response.answer.delta`
- `response.completed`

它校验：

- 事件名和 payload.event 一致；
- sequence 从 0 连续；
- request ID 不变；
- started/completed 只出现一次；
- delta 非空；
- completed 携带 response；
- 总缓冲不超过 1,000,000 字符；
- 流结束时必须 completed。

### 4.4 重试

前端只在网络中断、超时或 502/503/504 等可恢复场景提供人工“重新发送”。重试：

- 使用同一 request ID；
- 使用原问题和原 session ID；
- 不重复插入用户气泡；
- 提示可能的费用风险；
- 主动停止、401、409、422 不提供重试。

### 4.5 游客 Agent 记忆

```text
localStorage key: ai-nav:guest-agent:v1
最多 10 个对话
每对话最多 40 条消息
7 天 TTL
提交 Provider 的历史上限概念在游客路径中仍受 12 条/12000 字符限制
```

游客调用永远走纯 deterministic orchestrator，不调用外部 Provider。登录后不会自动把游客 Agent 对话导入服务端。

## 5. 配置边界

### 5.1 默认开发语义

```text
AI_NAV_AGENT_PROVIDER=deterministic
AI_NAV_AGENT_PROVIDER_LIVE_ENABLED=0
AI_NAV_AGENT_STREAM_ENABLED=0
AI_NAV_AGENT_SESSIONS_ENABLED=0
AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO=0
AI_NAV_API_WORKERS=1
AI_NAV_AGENT_RUNTIME_STATE_BACKEND=process_local
```

`start.ps1` 为本地产品体验默认开启游客聊天和会话，但仍保持 live Provider 关闭。

### 5.2 生产启动硬校验

生产会拒绝：

- 默认或短 `SECRET_KEY`
- 通配/非 HTTPS/带路径的 CORS origin
- 不安全 Refresh Cookie
- 源码树内数据库或上传目录
- `RESET_DATABASE_ON_START=1`
- FakeProvider
- live 与非 openai-compatible 组合
- 非北京百炼允许主机
- 默认模型漂移
- 候选模型漂移或比例非 0
- 多 worker
- 非 `process_local`
- 不安全保留期或成本阈值

## 6. 发布与回滚

### 6.1 Provider 最小回滚

```text
LIVE_ENABLED=0
PROVIDER=deterministic
UPGRADE_RATIO=0
```

必要时再关闭 SSE 和 Sessions。数据库迁移保留，不做破坏性回滚。

### 6.2 应用回滚

- 切回旧 release 指针；
- Nginx 配置先 `nginx -t`；
- 只有确认数据损坏时才从验证备份恢复；
- 恢复演练使用隔离数据库，拒绝覆盖 live；
- 重新跑 health、security 和 smoke。

## 7. 测试与证据

### 7.1 门禁入口

```text
verify-quality.ps1
verify-foundation.ps1
verify-frontend.ps1
verify-tools.ps1
verify-learning.ps1
verify-users.ps1
verify-agent.ps1
verify-http-test-deployment.ps1
verify-production-deployment.ps1
```

Foundation 当前顺序：

1. Frontend
2. Tools
3. Learning/Platform
4. Users/发布安全
5. HTTP 测试部署
6. 生产部署准备

Agent 单独运行，避免 Provider 可用性耦合普通网站门禁。

### 7.2 当前静态盘点

分析时源码静态统计：

- Python `test_*` 方法约 281 个
- 其中 `test_agent*.py` 约 115 个
- Node 测试源码约 80 个显式 `test(...)`；部分文件使用封装或别名，静态正则可能低估

这些是源码盘点，不是执行结果。

### 7.3 最近可复核的执行证据

仓库文档中最近的全项目已执行记录包括：

- 2026-07-29：264 项 Python，分支覆盖率 86.5%
- 前端 Node 77/77
- 更早独立整改：176/176 Python、34/34 Node、85.9% 总覆盖率
- 2026-07-25 Agent 完成审计：91 Python + 3 Node/SSE

当前代码后来增加了游客 Agent、HTTP 部署、性能、生产覆盖层和快捷助手测试，因此旧执行数字不能当成当前工作树的完整通过证明。

### 7.4 本次没有做的事

- 没有重新执行全量测试；
- 没有启动服务；
- 没有写数据库；
- 没有生成覆盖率；
- 没有联网调用 Provider；
- 没有验证生产域名或服务器；
- 没有修改现有测试产物。
