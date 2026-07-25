# 用户层优化新对话提示词

将下方内容完整发送给新的 Codex 对话：

```text
你负责当前项目的“用户层企业级优化”任务。请在现有工作区持续实施，直到本阶段目标真正完成，不要只给计划或停在分析。

工作区：D:\Web期末作业\ai-nav2\ai-nav-fullstack

开始前必须阅读：
1. docs/03-domains/users/users-area-optimization-guide.md
2. docs/03-domains/users/users-area-task-backlog.md
3. docs/01-overview/project-wide-optimization-roadmap.md
4. docs/03-domains/users/user-module-design.md（仅作为早期模型参考，发现与代码冲突时以当前代码和新指导为准）
5. docs/03-domains/learning/learning-area-implementation.md
6. backend/app/users/learning_state/（作为 service/port/repository 的已验证范式）
7. backend/app/api/v1/routers/auth.py、users.py、user_learning.py
8. frontend/settings.html、frontend/assets/js/settings.js、auth-ui.js、api.js
9. database/schema.sql 与 database/migrations/

总目标：
- 把用户层建设为可独立测试、可复用、可审计的身份和私有状态服务。
- 逐步将 auth.py/users.py 中的 SQL 与业务规则迁移到 Users 子域 service、policy、repository port 和 SQLite adapter。
- 完善账号、认证安全、资料、偏好、会话、授权、隐私和用户资产体验。
- 保持现有 URL 兼容，并满足企业级迁移、契约、测试、安全、可观测性和浏览器验收标准。

必须遵守的边界：
- Learning 是无用户身份的事实服务；不得修改其表来保存用户状态。
- users.learning_state 已完成，除修复明确契约问题外不得重写其进度、章节、最近阅读和收藏规则。
- Users 可调用 Learning/Tools 的公开 read facade 补齐事实，但不得直接读取领域表。
- Agent 只能通过 Users facade 读取最小必要上下文；写用户状态或资产必须经过确认、幂等、授权和审计。
- 共享限流、密钥管理、集中指标和分布式缓存属于 Platform；Users 只接入抽象，不手写不可扩展替代品。
- 不制造假用户数据、假会话、假工作流或前端示例状态。

工程要求：
- 先检查工作区已有修改，保留并理解现有未归档内容，绝不回滚其他任务成果。
- 使用新增迁移，不修改已经执行的 001/002/003；迁移必须通过 checksum 检查。
- SQL 只允许存在于 repository；HTTP router 必须保持薄。
- DTO 默认 extra=forbid；错误使用稳定 detail.code/message。
- 所有私有查询从认证上下文获取 user_id，不接受客户端 userId。
- 敏感字段不得进入日志、审计 metadata、普通 DTO 或浏览器持久存储。
- 写操作考虑事务、幂等、版本冲突、审计和失败回滚。
- 前端使用独立 users-api.js，提供 loading/empty/error/retry/saving/success 状态。
- 采用现有 UI 风格，设置页保持安静、紧凑、工作台式布局。

执行顺序：
1. 审计并冻结 auth/users 当前契约、响应、数据库和桌面/移动行为。
2. 建立测试数据库注入、严格 DTO、稳定错误和 Users CI/verify 脚本。
3. 创建 account/profile/preferences/sessions/security/authorization 子域骨架。
4. 将 users.py 的 SQL 和业务规则迁移到 repositories/services，保持接口兼容。
5. 将 auth.py 按 authentication/security/session 边界逐步迁移；先保持现有令牌协议，再在测试覆盖后做刷新轮换与 Cookie 迁移。
6. 收口前端用户 API 和设置页异步状态。
7. 执行单元、repository、service、API、安全、Playwright 和移动端验证。
8. 更新指导文档和任务状态，清理 QA 用户与测试数据。

首批验收目标：
- 完成 docs/03-domains/users/users-area-task-backlog.md 中 USR-001 至 USR-105。
- auth/users 当前公开 URL 不发生无说明的破坏性变化。
- users.py 的核心账号、资料、偏好和会话 SQL 已离开路由。
- service/repository 可在不启动 FastAPI 时测试。
- 跨用户隔离、额外字段拒绝、401/404/409/422 和迁移漂移有测试。
- 保留 scripts/verify-users.ps1 并接入 Foundation CI，任何原生命令失败都必须让验证失败。
- 学习区现有 .\scripts\verify-learning.ps1 继续通过。
- 启动本地服务，使用 Playwright 检查设置页桌面和 390px 移动视口，无横向溢出和应用控制台错误。

工作方式：
- 边探索边实施，每完成一个任务就更新清单状态。
- 每次编辑前说明即将修改的边界；每约 30 秒给出简短进展。
- 不要为了追求目录形式而制造空抽象；沿用 users.learning_state 已证明有效的模式。
- 遇到安全取舍时选择渐进兼容方案，并在文档中记录威胁、迁移和回滚策略。
- 阶段完成后给出变更摘要、验证证据、剩余风险和下一批任务，不要仅声称“完成”。
```

## 对话交接说明

这个新对话拥有 Users/Auth 的实现责任，但不拥有 Learning、Tools 或 Agent 的领域事实。遇到跨域需求时先定义 facade/contract，再把对应实现任务交给所属分区；不得通过跨模块 SQL 快速绕过边界。
