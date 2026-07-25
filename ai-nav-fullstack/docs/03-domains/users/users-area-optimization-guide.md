# 用户层企业级优化指导

版本：v1.1  
日期：2026-07-14  
适用仓库：`D:\Web期末作业\ai-nav2\ai-nav-fullstack`

## 1. 文档定位

本文件是下一轮用户层优化的执行指导。`docs/03-domains/users/user-module-design.md` 保留为早期数据模型参考，但其中“用户体系尚未建设”“学习状态未落地”等描述已经过时；当前事实必须以代码、迁移和本文件为准。

用户层不是设置页或登录弹窗的同义词，而是全系统的身份、私有状态、授权、隐私和用户资产服务。Web、Learning、Tools 和 Agent 只能通过 Users 的公开 facade 使用用户能力，不得直接查询用户表。

## 2. 当前基线

已经具备：

- 账号注册、登录、刷新、退出、当前用户、用户名可用性和安全问题重置密码。
- 账号、密码、资料、头像、偏好、会话、角色权限、登录日志和审计表。
- 设置页中的资料、账号、安全、会话、偏好、学习空间和工作流入口。
- 独立 `backend/app/users/learning_state/`，已实现进度、章节、活动、最近阅读、继续学习、收藏、匿名导入、版本冲突、幂等和审计。
- 版本化迁移、严格学习 DTO、学习区 CI 和浏览器回归基线。

以下是 2026-07-12 启动优化时的缺口，完成状态以 `docs/03-domains/users/users-area-task-backlog.md` 和
`docs/01-overview/project-wide-optimization-roadmap.md` 为准，不再据此继续增加分层：

- `auth.py` 和 `users.py` 仍同时承担 HTTP、SQL、事务和业务规则，难以独立测试。
- account/profile/preferences/sessions/security 当时尚未从路由中抽离；当前不要求每项能力继续维持独立 port/repository 包。
- 用户响应模型、错误码、分页和并发语义没有完全统一。
- 刷新令牌仍由前端持有，默认密钥和宽松 CORS 不适合生产环境。
- 登录限流、刷新令牌重放检测、风险会话、隐私导出/删除和数据保留策略尚不完整。
- `settings.js` 仍直接散落用户 API 路径，页面级 loading/error/retry/saving 状态不完全一致。
- 用户工作流仍是 reserved 接口，所有权和 Agent 边界尚未落地。
- auth/users 缺少独立服务测试、API 契约快照和安全回归矩阵。

## 3. 所有权边界

| 能力 | 所有者 | 允许依赖 | 禁止事项 |
| --- | --- | --- | --- |
| 账号身份、状态、软删除 | Users account | Auth、Admin | Learning/Agent 直接改账号表 |
| 密码、令牌、会话、重置 | Users security/auth | Platform 安全设施 | 页面保存密码或刷新令牌明文 |
| 资料、头像 | Users profile | 对象存储适配器 | Agent 擅自修改用户资料 |
| 偏好与授权同意 | Users preferences | Learning/Tools/Agent 只读 facade | 各领域复制偏好表 |
| 角色与权限 | Users authorization | 路由依赖、Admin | 仅靠前端隐藏按钮授权 |
| 学习进度、最近阅读、收藏 | Users learning_state | Learning 只读 facade | Learning 反向依赖 Users |
| 保存的工作流和计划 | Users assets | Agent/Tools 稳定引用 | Agent 把用户资产存进会话内部 |
| Agent 会话与生成过程 | Agent | Users 身份和同意 facade | Users 持有模型提示词与推理逻辑 |
| 限流、集中指标、密钥管理 | Platform | 所有服务 | Users 自建不可扩展的全局设施 |

## 4. 目标架构

```text
backend/app/users/
  identity/         # 账号、认证、安全、会话和授权
  settings/         # 资料、头像和偏好
  learning_state/   # 进度、活动、继续学习和收藏
  assets/           # 保存工作流和后续用户资产
  governance/       # 隐私、审计、命令安全和用户侧观测
```

以上是功能所有权分组，不要求立即搬迁已经验收的目录，也不代表独立部署服务。后续修改相关
功能时再渐进合并空泛层级。

默认采用：

```text
HTTP router -> module service -> SQLite repository
```

路由只处理认证依赖、参数、状态码和错误转换；SQL 只能出现在 repository；密码哈希、状态迁移、权限判断和令牌轮换属于 service。只有存在两个真实实现、外部系统边界或复杂可复用策略时，才增加 port、adapter、facade 或 policy。完整约束见 `docs/02-architecture/modular-monolith-guidelines.md`。

## 5. 身份与安全设计

### 5.1 账号与认证

- 对外只暴露 `userUid/sessionUid`，不得暴露自增主键。
- 用户名、邮箱和手机规范化后再执行唯一性判断。
- 注册、登录、刷新和重置请求必须有稳定错误码，避免泄露账号是否存在。
- 密码哈希参数、算法版本和升级策略集中在 security policy。
- 账号状态至少区分 `active/disabled/locked/deleted`，状态迁移必须审计。

### 5.2 Token 与会话

- 访问令牌短时有效；刷新令牌必须轮换、哈希存储、可撤销并检测重复使用。
- 优先迁移为 Secure、HttpOnly、SameSite 刷新 Cookie；访问令牌不长期落盘。
- 每次刷新校验 session、账号状态、过期时间、撤销状态和 token version。
- 修改密码、禁用账号和高风险操作后撤销相关会话。
- 会话列表只返回设备、位置、时间和状态等安全展示字段。

### 5.3 授权与隐私

- 权限在后端 policy/dependency 判断，前端仅负责展示。
- 所有私有查询必须使用服务端认证得到的 `user_id`，不得接受客户端 userId。
- 头像、资料、偏好、会话和资产修改写入审计日志，但不得记录密码、令牌或安全答案。
- 设计账号数据导出、删除申请、软删除、匿名化和保留期；物理删除必须有受控流程。

## 6. 用户体验要求

- 设置页保持工作台式布局，不改成营销页；资料、账号、安全、会话、偏好、学习和资产分别可定位。
- 每个异步区域必须有 loading、empty、error、retry、saving、success 状态。
- 修改账号、密码、安全问题、撤销会话等敏感操作需要明确确认和结果反馈。
- 会话页标识当前设备，并支持撤销单个其他会话和“退出其他设备”。
- 偏好保存后立即影响对应领域，但领域只消费 Users facade，不直接读取表。
- 学习空间继续复用 `users.learning_state`，不得重写进度算法或复制 Learning 内容。
- 工作流/计划没有真实数据时返回真实空集合；不得在前端制造示例用户资产。
- 360、390、768、1440 像素视口不得横向溢出；键盘焦点、表单标签和错误提示可访问。

## 7. 数据与迁移原则

- 不修改已经执行的迁移；新增 `004_*` 及后续迁移，并保留 checksum 校验。
- 新表/字段必须写明唯一约束、外键、索引、状态 CHECK、时间语义和删除策略。
- SQLite 写操作使用显式事务；未来迁移 PostgreSQL 时可映射到 RLS 和行锁。
- 账号、资料、偏好等一对一表保持 `UNIQUE(user_id)`；会话、审计、资产是一对多。
- 并发修改资料/偏好时引入 version 或等效条件更新，避免多标签页静默覆盖。
- PII、认证秘密、审计元数据分级处理，不把敏感字段拼进通用 DTO。

## 8. API 与契约原则

- 保持现有 `/api/v1/auth/*` 和 `/api/v1/users/me/*` URL，内部渐进迁移到 service。
- 所有请求/响应使用 `extra="forbid"` 的严格 DTO；错误统一为 `detail.code/message`。
- 列表统一 `items + page/pageSize/totalCount/hasNext`。
- 写操作明确幂等、并发和审计语义；敏感命令需要当前密码或短时验证凭证。
- 新增 `users-api.js` 集中前端用户 API，`settings.js/auth-ui.js` 不再散落路径。
- Agent 只获得最小必要用户上下文和授权同意，不返回密码、安全问题、令牌或完整审计记录。

## 9. 测试与工程门禁

- Policy 单元测试：账号状态、密码规则、权限、会话轮换、隐私策略。
- Repository 集成测试：唯一约束、事务回滚、用户隔离、并发版本和索引查询。
- Service 测试：注册、登录、刷新重放、改密撤销、资料/偏好更新和会话撤销。
- API 契约测试：401/403/404/409/422、稳定错误码和额外字段拒绝。
- 安全测试：账号枚举、暴力尝试、过期/撤销/错误类型 Token、跨用户读取。
- 前端测试：表单校验、保存状态、失败重试、会话操作和退出登录。
- Playwright：桌面/移动注册登录、资料修改、偏好、改密、会话撤销及学习状态不回归。
- 保留 `scripts/verify-users.ps1` 作为 Users 专项门禁，并由仓库根目录 `.github/workflows/ai-nav-foundation-ci.yml` 统一执行；原生命令非零退出必须使脚本失败。

## 10. 完成定义

- auth/users 路由不再包含业务 SQL。
- 核心子域均可在不启动 FastAPI 的情况下测试。
- 登录、刷新、改密、会话撤销、资料和偏好链路具有稳定契约和审计。
- 用户私有数据经过跨用户隔离测试，后端授权不可绕过。
- 学习区现有 12+2 测试和浏览器链路继续通过。
- 前端只有一个用户 API 适配入口，没有 reserved 假数据或重复旧脚本。
- 文档、迁移、OpenAPI、测试和运行行为一致。
