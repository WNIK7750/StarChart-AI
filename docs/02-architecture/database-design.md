# 数据库设计说明

当前版本使用 SQLite，表结构按可迁移到 MySQL/PostgreSQL 的方式设计：

- 所有业务实体使用自增主键，并额外保留稳定业务编码，例如 `slug`、`code`。
- 可展示数据都包含 `sort_order` 和 `is_active`，方便运营排序和软下线。
- 内容表保留 `created_at`、`updated_at`，便于后续接入后台管理和审计。
- 多对多关系使用中间表，例如 `roadmap_domain_nodes`、`workflow_tools`。
- 关键查询字段建立索引，例如工具分类、学习资源节点、路线图边。

核心表：

- `navigation_items`：顶部导航。
- `difficulty_levels`：路线图难度字典。
- `knowledge_domains`：知识领域 tabs。
- `roadmap_nodes` / `roadmap_edges`：知识地图节点和连接线。
- `roadmap_domain_nodes`：领域与节点的多对多关系。
- `learning_resources`：学习页推荐卡片。
- `learning_materials`：学习节点主资料，使用 `is_primary` 标记每个节点最推荐的学习资料。
- `learning_material_sections`：主资料目录，保存章节、目录节点、建议学习时长和来源地址。
- `learning_node_tags`：学习节点标签。
- `learning_node_links`：节点资料池，保存视频、课程、文档、指南等补充资料。
- `tool_categories` / `tool_subcategories` / `ai_tools`：工具库标准三层结构。
- `tool_workflows` / `workflow_tools`：工具工作流。
- `user_accounts`：用户账号主表。
- `user_auth_passwords`：密码 hash 与登录失败计数。
- `user_security_questions`：用户密保问题与答案 hash，用于登录页找回密码；答案不明文返回前端。
- `user_profiles`：用户展示资料。
- `user_preferences`：用户推荐与 Agent 偏好。
- `user_sessions`：登录会话和刷新令牌 hash。
- `roles` / `permissions` / `role_permissions` / `user_role_assignments`：RBAC 权限模型。
- `user_login_logs` / `user_audit_logs`：登录与审计记录。

## 学习资料访问标准

学习资料表统一使用 `access_type` 表示访问条件：

- `cn`：国内可访问，优先用于国内用户的学习路径。
- `external`：外网资料，前端显示“外网”标签。

资料类型使用 `link_type` 或 `material_type` 表示，例如：

- `video`：视频课程。
- `course`：体系化课程。
- `documentation`：官方文档。
- `guide`：实践指南。
- `book`：书籍或在线教材。

## 学习节点详情页数据来源

节点介绍页通过 `GET /api/v1/learning/nodes/{slug}` 获取数据，接口返回：

- `node`：节点基础信息。
- `mainMaterial`：主资料。
- `overview`：根据主资料整理出的学习概览。
- `outline`：主资料目录。
- `resources`：资料池，不包含用户个人进度。
- `tags`：节点标签。
- `stats`：章节数、目录节点数和建议学习时长。
- `navigation`：前后相邻节点。

建议学习时长由 `learning_material_sections.duration_minutes` 自动汇总，避免前端维护重复的虚假数据。

## 用户模块设计

用户模块按认证、资料、偏好、权限和审计分层，避免把所有字段塞进单张用户表。

- 对外暴露 `user_uid`，不暴露自增主键。
- 密码使用 hash 存储，第一阶段为 `pbkdf2_sha256`，后续可迁移到 Argon2id。
- Refresh Token 只保存 HMAC hash。
- 高频筛选字段和外键字段均建立索引。
- 当前 SQLite 阶段保留迁移到 PostgreSQL RLS 的数据边界：用户私有表均以 `user_id` 作为隔离字段。
