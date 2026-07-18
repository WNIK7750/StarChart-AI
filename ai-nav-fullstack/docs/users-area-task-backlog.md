# 用户层优化任务清单

状态约定：`[ ]` 未开始，`[~]` 进行中，`[x]` 完成。每个任务必须同时提交实现、测试、迁移/契约说明和验证证据。

## U0 基线与护栏（P0）

- [x] `USR-001` 冻结现有 auth/users OpenAPI、真实响应样例和桌面/移动截图。
- [x] `USR-002` 建立 auth/users 测试数据库注入、严格 DTO、稳定错误映射和契约快照。
- [x] `USR-003` 新增 `verify-users.ps1` 并接入现有 Foundation CI，修复所有可能产生假绿的命令检查。
- [x] `USR-004` 建立安全基线：密钥、CORS、Token 存储、密码策略、账号枚举、会话和审计检查。
- [x] `USR-005` 记录现有登录/刷新/资料/设置链路性能与数据库查询基线。

验收：现状可重复验证；后续重构发生契约或安全回归时 CI 必须失败。

## U1 用户领域分层（P0）

- [x] `USR-101` 建立 account/profile/preferences/sessions/security/authorization 子域目录和 repository ports。
- [x] `USR-102` 将 `users.py` 中账号、资料、头像、偏好、会话 SQL 迁入 SQLite repositories。
- [x] `USR-103` 将业务校验、状态迁移、审计和事务迁入 services/policies。
- [x] `USR-104` 将用户路由改成薄适配器，并保持现有 URL 兼容。
- [x] `USR-105` 统一 Users 错误体系、分页元数据、时间格式和对外稳定 UID。

验收：路由无业务 SQL；service/repository 可独立测试；学习状态子域不被破坏。

## U2 认证与会话安全（P0）

- [x] `USR-201` 抽取 authentication/security service，集中注册、登录、刷新、退出和重置流程。
- [x] `USR-202` 实现刷新令牌轮换、哈希存储、令牌族/重放检测和全族撤销策略。
- [x] `USR-203` 规划并迁移 Secure HttpOnly SameSite 刷新 Cookie；提供兼容和回滚策略。
- [x] `USR-204` 完善密码哈希版本升级、改密后会话撤销和敏感操作再验证。
- [x] `USR-205` 完善失败尝试、临时锁定、登录日志和不泄露账号存在性的错误响应。
- [x] `USR-206` 完善当前会话识别、撤销其他会话、退出其他设备和风险状态。

验收：过期、撤销、重放、错误类型和旧 token version 全部失败；无令牌明文进入日志或数据库。

## U3 资料、偏好与设置体验（P1）

- [x] `USR-301` 为资料和偏好增加并发版本或条件更新，返回 409 并支持前端恢复。
- [x] `USR-302` 建立 `users-api.js`，收口 `settings.js/auth-ui.js` 的用户接口路径。
- [x] `USR-303` 统一设置页各区域 loading/empty/error/retry/saving/success 状态。
- [x] `USR-304` 完善头像上传校验、裁剪、尺寸/格式限制、旧文件清理和失败回滚。
- [x] `USR-305` 完善账号、密码、安全问题和会话操作的确认、可访问性和移动端体验。
- [x] `USR-306` 确保偏好通过 Users facade 供 Learning/Tools/Agent 消费，不复制状态。

验收：设置页在 360/390/768/1440 下无溢出；多标签页更新不静默覆盖。

## U4 授权、审计与隐私（P1）

- [x] `USR-401` 将 RBAC 查询和权限判断抽为 authorization policy/dependency。
- [x] `USR-402` 为敏感用户命令定义审计事件、资源标识和脱敏元数据规范。
- [x] `USR-403` 增加跨用户隔离、普通用户/运营/管理员权限测试。
- [x] `USR-404` 设计用户数据导出、删除申请、软删除、匿名化、恢复与保留期。
- [x] `USR-405` 增加隐私同意版本和 Agent memory consent 的读取/撤销契约。

验收：权限只由后端决定；删除与导出流程可审计且不会破坏公共领域事实。

## U5 用户资产与跨域 facade（P1/P2）

- [x] `USR-501` 明确 `user_saved_workflows`、学习计划和其他资产的所有权及稳定引用。
- [x] `USR-502` 实现 assets service、分页 API、版本控制、归档和审计；移除 reserved 工作流接口。
- [x] `USR-503` 提供面向 Agent 的最小用户上下文 facade，包含偏好、授权和资产摘要。
- [x] `USR-504` Agent 写入资产必须经过用户确认、幂等键、Users 命令接口和审计。
- [x] `USR-505` 领域目标下线时保留用户资产并返回 unavailable 状态，不静默删除。

验收：Agent、Learning、Tools 均不访问用户表；替换 Agent 框架不影响用户资产结构。

## U6 可观测性与发布（贯穿）

- [x] `USR-601` 用户接口记录 requestId、operation、latency、status、errorCode，不记录 PII/秘密。
- [x] `USR-602` 建立注册、登录、刷新、锁定、改密和会话撤销指标与告警接口。
- [x] `USR-603` 建立迁移演练、备份恢复、回滚步骤和发布检查单。
- [x] `USR-604` 建立用户关键路径性能预算和慢查询检查。
- [x] `USR-605` 完成最终 OpenAPI、数据库、前端、桌面/移动和安全验收报告。

## 首个实施批次

新对话首先执行 `USR-001` 至 `USR-105`。只有基线、测试和领域分层完成后，才进入 Token/Cookie 迁移；不得在没有回归保障时一次性重写认证协议。

## 2026-07-12 首批实施记录

- 已新增 `backend/app/users/account/`、`profile/`、`preferences/`、`sessions/`、`security/`、`authorization/` 子域，包含 service、repository port 和 SQLite adapter。
- 已将 `backend/app/api/v1/routers/users.py` 中账号、资料、头像持久化、偏好、会话、密码和密保问题 SQL 迁入 Users repositories/services；路由保留现有 `/api/v1/users/me/*` URL。
- 已新增 `tests/test_users_services.py` 和 `tests/contracts/users_contract_v1.json`，覆盖临时 SQLite 注入、严格 DTO、跨用户隔离、409 用户名冲突、401 密码错误、会话撤销、密保答案 hash、authorization facade。
- 已新增 `scripts/verify-users.ps1`，现由仓库根目录 `.github/workflows/ai-nav-foundation-ci.yml` 统一调用；脚本设置 `PYTHONPATH=backend`，优先使用本地 `.venv`，并执行编译、Users service tests、`git diff --check`。
- 验证证据：`.\scripts\verify-users.ps1` 通过，7 项 Users 测试通过；`.\scripts\verify-learning.ps1` 通过，包含 19 项 Python 单测、2 项前端学习测试、内容检查和性能基线。
- 当时尚未完成：auth.py 分层、完整 OpenAPI/真实响应冻结、桌面/移动截图、安全基线矩阵、性能/查询基线、分页统一和 profile/preferences 并发版本 409；后续记录已逐项收口。

## 2026-07-12 认证分层实施记录

- 已新增 `backend/app/users/authentication/` 子域，包含 `service.py`、repository port 和 SQLite adapter。
- 已将 `backend/app/api/v1/routers/auth.py` 改为薄 HTTP 适配器，注册、登录、刷新、退出、当前用户和密保重置流程保持现有 URL/响应形状。
- `auth.py` 和 `users.py` 路由 SQL 扫描均为空；认证、账号、资料、偏好、会话、密保和 authorization 查询已迁入 Users repositories/services。
- 已扩展 `tests/test_users_services.py` 到 10 项，新增注册、登录失败 401、当前用户 token、刷新、退出、密保重置和会话撤销测试。
- 验证证据：`.\scripts\verify-users.ps1` 通过，10 项 Users/Auth 测试通过；`.\scripts\verify-learning.ps1` 通过，包含 22 项 Python 单测、2 项前端学习测试、内容检查和性能基线。
- 当时尚未完成：`USR-001` 的 OpenAPI/真实响应/截图冻结，`USR-004` 安全基线矩阵，`USR-005` 性能与查询基线，`USR-105` 的所有列表分页和时间格式全局统一；后续记录已完成 `USR-001`、`USR-004`、`USR-005`。

## 2026-07-12 基线护栏实施记录

- 已新增 `scripts/freeze-users-contracts.py`，生成 `docs/users-baseline/auth_users_openapi.json` 和 `docs/users-baseline/auth_users_response_shapes.json`，冻结 auth/users OpenAPI 与真实服务响应字段形状。
- 已新增 `scripts/check-users-security-baseline.py`，生成 `docs/users-baseline/users_security_baseline.json`；当前结果为 3 pass、3 known-risk、0 fail。已知风险为默认开发密钥、宽松 CORS、refresh token 存在 localStorage。
- 已新增 `scripts/benchmark-users.py`，生成 `docs/users-baseline/users_performance_baseline.json`，记录当前用户关键链路耗时和 SQL 语句数：current_user p95 约 0.9ms/1 statement，refresh p95 约 1.7ms/2 statements，profile/preferences/sessions 读取 p95 均小于 1ms/1 statement。
- `scripts/verify-users.ps1` 已接入契约冻结、安全基线和性能基线生成，非零退出会让验证失败。
- 验证证据：`.\scripts\verify-users.ps1` 通过；`.\scripts\verify-learning.ps1` 通过。
- 该阶段完成后 `USR-001` 仍缺桌面/移动截图冻结；已在后续“设置页截图冻结记录”中补齐。

## 2026-07-12 设置页截图冻结记录

- 已新增 `scripts/capture-users-screenshots.ps1`，脚本使用临时 `@playwright/test` 安装，不修改仓库依赖；要求本地服务已通过 `AI_NAV_BASE_URL` 或默认 `http://127.0.0.1:8000` 可访问。
- 已冻结设置页认证态截图到 `docs/users-baseline/screenshots/`：`settings-desktop-1440.png`、`settings-mobile-390.png`，并保存对应 JSON 与 `settings-screenshots-manifest.json`。
- 验证流：`settings.html#profile` -> 注入真实注册用户 token -> 进入设置页 -> 点击偏好导航 -> `preferences` 区域渲染。
- 验证结果：桌面 1440x900 与移动 390x844 均无横向溢出，浏览器 console 无 error/warning，页面标题为 `用户设置 · AI 知识导航`，active section 为 `preferences`。
- `USR-001` 已完成；后续视觉回归可以复用该脚本，但它未接入默认 CI，避免 CI 因临时浏览器安装而变慢。

## 2026-07-12 Users 契约收口记录

- 已为 `/api/v1/users/me/sessions` 增加兼容分页参数 `page` 与 `pageSize`，响应保持 `items`，并新增 `meta.page/pageSize/totalCount/hasNext/source/contractVersion`。
- `settings.js` 继续只消费 `items`，因此该增强对现有设置页兼容；后续可以在 UI 上增加“加载更多设备”。
- 已扩展 `tests/test_users_services.py`，覆盖 sessions 分页元数据和跨用户隔离；Users/Auth 测试增加到 11 项。
- 已刷新 `docs/users-baseline/auth_users_response_shapes.json`、`tests/contracts/users_contract_v1.json` 和 `docs/users-baseline/users_performance_baseline.json`；sessions list 当前基线为 2 statements（count + page list）。
- 验证证据：`.\scripts\verify-users.ps1` 通过；`.\scripts\verify-learning.ps1` 通过，包含 23 项 Python 单测。
- 至此首批 `USR-001` 至 `USR-105` 已完成；Token/Cookie 迁移仍按清单进入 U2，不在本批无回归保障地重写协议。

## 2026-07-14 Refresh Token 轮换记录

- 已新增 `database/migrations/004_refresh_token_rotation.sql`，为 `user_sessions` 增加 `token_family_uid`、`parent_session_id`、`replaced_by_session_id` 和 `revoked_reason`，既有会话回填 `token_family_uid=session_uid`。
- `/api/v1/auth/refresh` 保持原有请求兼容，响应新增 `refreshToken`；刷新时旧 session 标记为 `rotated`，新 session 继承同一 token family。
- rotated refresh token 再次使用时返回稳定错误 `REFRESH_TOKEN_REPLAYED`，并撤销同族 active sessions，防止旧 token 重放继续换取访问令牌。
- logout、密码修改和密保重置会写入 `revoked_reason`（`logout`、`password_changed`、`password_reset`），便于后续会话风险展示和审计。
- 已扩展 `tests/test_users_services.py` 到 12 项，覆盖 refresh token 轮换、重放检测、同族撤销、密码修改/重置撤销原因。
- 已刷新 auth/users 契约与性能基线；`auth.refresh_rotate` 当前基线为 p95 约 5.9ms、4 statements。
- 验证证据：`.\scripts\verify-users.ps1` 通过；`.\scripts\verify-learning.ps1` 通过，包含 24 项 Python 单测。
- 后续补齐：Secure Cookie 配置、临时锁定、当前会话识别与风险状态展示已在下方 2026-07-14 记录中完成。

## 2026-07-14 Refresh Cookie 兼容迁移记录

- 登录、注册和刷新成功后会写入 `ai_nav_refresh_token` HttpOnly SameSite=Lax Cookie，路径默认限定为 `/api/v1/auth`；刷新响应仍保留 `refreshToken` 字段，便于旧客户端兼容和回滚。
- `/api/v1/auth/refresh` 与 `/api/v1/auth/logout` 优先读取 Cookie，缺失时回退读取请求体 `refreshToken`，旧 body 协议仍可用。
- 前端 `api.js` 已为同源请求启用 `credentials: "same-origin"`，不再写入 `localStorage.setItem("ai_nav_refresh_token", ...)`；仅清理旧本地 refresh token，保留 access token 兼容现有页面鉴权。
- 安全基线已新增 HttpOnly/SameSite/Secure 配置化 Cookie 检查，并将 refresh token localStorage 写入作为失败项；Users 单测新增 Cookie 优先、body 回退和清理 Cookie 覆盖。
- Cookie 策略已配置化：`AI_NAV_REFRESH_COOKIE_SECURE=1` 可在生产启用 Secure，另有 `AI_NAV_REFRESH_COOKIE_NAME`、`AI_NAV_REFRESH_COOKIE_PATH`、`AI_NAV_REFRESH_COOKIE_SAMESITE` 和 `AI_NAV_REFRESH_COOKIE_MAX_AGE_SECONDS` 用于部署调整；默认本地开发保留 `secure=False`。
- 验证证据：`.\scripts\verify-users.ps1` 通过，13 项 Users/Auth 单测；`.\scripts\verify-learning.ps1` 通过，包含 25 项 Python 单测、2 项前端学习测试、内容检查和性能基线。
- 回滚策略：若 Cookie 迁移出现客户端兼容问题，保留 body `refreshToken` fallback 与响应字段即可临时回退；迁移期结束后再单独移除 body fallback。

## 2026-07-14 密码哈希升级与敏感操作再验证记录

- 密码哈希轮数已通过 `AI_NAV_PASSWORD_HASH_ROUNDS` 配置化，默认保持 `pbkdf2_sha256$180000$...` 格式；`needs_password_rehash` 会识别低轮数或未知算法 hash。
- 登录成功后若检测到旧 hash，会静默重算并写回当前轮数；注册、改密和密保重置会直接写入当前版本 hash。
- 修改密码继续要求当前密码，成功后递增 `token_version` 并以 `password_changed` 撤销 active sessions；替换密保问题也要求当前密码，验证成功后会刷新旧 hash。
- 安全基线新增 `USR-SEC-007`，覆盖 hash 轮数配置、登录升级和敏感操作 reauth 后升级能力。
- 验证证据：`.\scripts\verify-users.ps1` 通过，14 项 Users/Auth 单测；新增 `test_successful_login_upgrades_legacy_password_hash` 覆盖旧 hash 登录升级。

## 2026-07-14 登录失败锁定记录

- 登录失败计数和临时锁定已配置化：`AI_NAV_LOGIN_MAX_FAILED_ATTEMPTS` 默认 5 次，`AI_NAV_LOGIN_LOCK_MINUTES` 默认 15 分钟。
- 达到阈值后写入 `user_auth_passwords.locked_until`；锁定期内即使密码正确也不会签发 token，成功登录会清空 `failed_attempts` 和 `locked_until`。
- 对外仍统一返回 `INVALID_CREDENTIALS`，避免通过错误码区分账号不存在、密码错误或账号处于锁定状态；登录日志仍记录失败事件供后续审计/指标使用。
- 安全基线新增 `USR-SEC-008`，覆盖失败计数、临时锁定配置和统一错误响应。
- 验证证据：`.\scripts\verify-users.ps1` 通过，15 项 Users/Auth 单测；新增 `test_login_failures_temporarily_lock_without_revealing_account_state` 覆盖锁定与解锁路径。

## 2026-07-14 会话识别与退出其他设备记录

- `/api/v1/users/me/sessions` 会在存在 refresh Cookie 时标记当前会话 `isCurrent=true`，并返回 `revokedReason` 与 `riskLevel`；sessions contract version 升级为 2。
- 新增 `POST /api/v1/users/me/sessions/revoke-others`，优先保留当前 refresh Cookie 对应会话，撤销同一用户其他 active sessions；无 Cookie 时仍可撤销全部 active sessions 作为兼容兜底。
- 单个会话撤销会写入 `revoked_reason='logout'`；重放检测会展示为高风险，密码变更/重置等系统撤销展示为中风险，普通已退出展示为 ended。
- 设置页设备列表会展示当前设备和风险标签，并提供“退出其他设备”操作；当前设备不显示单个撤销按钮。
- 安全基线新增 `USR-SEC-009`，覆盖当前会话识别、风险状态和 revoke-others API。
- 验证证据：`.\scripts\verify-users.ps1` 通过，16 项 Users/Auth 单测；新增 `test_sessions_mark_current_and_revoke_other_devices` 覆盖当前会话、风险状态和跨用户隔离撤销。

## 2026-07-14 资料并发控制与前端接口收口记录

- 新增 `database/migrations/005_user_profile_preference_versions.sql`，为 `user_profiles` 和 `user_preferences` 增加从 1 开始递增的 `version`。
- 资料和偏好更新改为 `user_id + expectedVersion` 条件写入；成功后原子递增版本，陈旧版本分别返回 `PROFILE_VERSION_CONFLICT` 或 `PREFERENCES_VERSION_CONFLICT`，HTTP 状态为 409。
- 设置页保存资料和偏好时携带当前版本；发生冲突后重新读取服务器版本，同时保留当前表单输入，提示用户检查后再次保存。头像更新也递增并回传资料版本，避免上传后产生假冲突。
- 新增 `frontend/assets/js/users-api.js`，集中 Auth/Users 路径；`settings.js` 与 `auth-ui.js` 已改用具名 facade 方法，路径扫描不再出现散落的 `/auth/*` 或 `/users/*` 字符串。
- 新增 `tests/test_users_frontend.mjs` 并接入 `verify-users.ps1`；验证 facade URL、方法、body、会话 UID 编码、Authorization 和同源 Cookie 请求配置。验证脚本同时改为逐命令传播失败状态。
- 验证证据：`.\scripts\verify-users.ps1` 通过，18 项 Users/Auth 单测和前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，30 项 Python 测试、2 项前端学习测试及内容/性能检查通过。
- 真实 HTTP 双客户端验证：首个更新将 profile 版本从 1 推进到 2，陈旧版本提交返回 `409 / PROFILE_VERSION_CONFLICT`，未发生静默覆盖。
- Playwright 验证：`settings.html#profile` 登录后切换偏好区、修改并保存偏好，1440x900 与 390x844 均出现成功反馈、无横向溢出、无 console/page error；Browser plugin 不可用，因此复用项目 Playwright 截图脚本。

## 2026-07-14 设置页统一状态记录

- `settings.js` 新增共享表单状态和内容状态 helper，统一处理 `loading/idle/saving/success/error/empty`；表单加载或保存期间设置 `aria-busy=true`、禁用控件并显示稳定按钮文案，完成后恢复。
- 资料、账号、密保和偏好加载从单个 `Promise.allSettled` 静默分支拆为独立区域 loader；失败时显示 `aria-live` 错误和局部“重试”按钮，重试只请求对应区域，不重置其他已加载表单。
- 会话、学习空间和工作流统一使用 loading/empty/error 状态块；会话撤销、退出其他设备和移除收藏增加进行中状态、局部错误恢复和按域刷新，不再让未捕获异常进入控制台。
- 资料、用户名、密码、密保问题和偏好保存统一使用 saving/success/error 状态；资料和用户名保存后只更新相关展示信息，避免重新加载全部设置并覆盖其他区域的未提交输入。
- `settings.html` 增加禁用态、状态反馈、重试按钮和轻量加载指示样式；状态尺寸稳定，桌面与移动布局没有额外位移或横向溢出。
- Playwright 状态验证：桌面端注入一次 sessions 503，确认局部错误、重试按钮和恢复后的设备列表；桌面与移动端均暂停偏好 PATCH，确认 `aria-busy=true` 和提交按钮禁用，放行后恢复并显示成功反馈。预期 503 单独记录，未知 console/page error 为 0。
- 验证证据：`.\scripts\verify-users.ps1` 通过，18 项 Users/Auth 单测和前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，30 项 Python 测试、2 项前端学习测试及内容/性能检查通过；Playwright 1440x900、390x844 两项通过。

## 2026-07-14 头像上传事务与校验记录

- 新增 `backend/app/users/profile/avatar.py`，头像解码、格式识别、EXIF 方向处理、透明背景合成、尺寸缩放、WebP 压缩和文件生命周期已从 HTTP 路由迁入 Users/profile 子域。
- 后端同时校验声明 Content-Type 与真实图片格式，支持 JPG、PNG、WebP、GIF；新增 `AVATAR_MAX_SOURCE_PIXELS` 默认 2000 万像素，并保留上传字节、输出字节和最大边长配置，阻止压缩炸弹和超限图片。
- 输出文件先写入同目录临时文件、刷新并通过 `os.replace` 原子替换；资料持久化失败时删除新文件，成功后只清理 `/uploads/avatars/*.webp` 管理范围内的旧头像，路径穿越或外部 URL 不参与删除。
- `ProfileUpdate` 不再接受 `avatarUrl`，头像只能通过专用上传命令更新，避免绕过文件校验、版本递增和旧文件清理。
- 前端改为精确 MIME 白名单，图片解码后检查像素总量并释放 Object URL；裁剪生成和上传期间设置 `aria-busy`、禁用确认按钮，失败时保留裁剪状态供用户重试。
- 新增头像服务测试，覆盖格式伪装、像素上限、WebP 输出、尺寸限制、连续替换旧文件、缺失用户导致的数据库更新失败回滚和临时文件清理；Users/Auth 测试增至 20 项。
- 安全基线新增 `USR-SEC-010`，检查像素上限、内容格式匹配、原子文件替换、失败回滚和薄路由边界；当前基线无新增 fail。
- Playwright 桌面验证：选择 PNG、打开裁剪器、上传 WebP、头像 URL 更新；连续上传第二张后，第一张头像 URL 返回 404。1440x900 与 390x844 回归均通过，未知 console/page error 为 0。
- 验证证据：`.\scripts\verify-users.ps1` 通过，20 项 Users/Auth 单测和前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，32 项 Python 测试、2 项前端学习测试及内容/性能检查通过。

## 2026-07-14 设置可访问性与跨域偏好记录

- 设置页新增统一原生确认对话框；修改用户名、密码、密保问题、撤销单个会话和退出其他设备均需明确确认，取消或 Escape 会关闭对话框并把焦点还给触发控件。
- 侧栏当前分区增加 `aria-current`，静态与动态表单标签均绑定真实控件；头像裁剪器补充 dialog 语义、标题、缩放标签、关闭按钮名称、Escape 关闭和焦点恢复。
- 360/390/768/1440 四个视口统一验证触控尺寸、标签关联、当前分区、保存中状态和横向溢出；Playwright 4 项通过，未知 console/page error 为 0，截图清单 `passed=true`。
- 新增 `UserPreferencesFacade` 和 `GET /api/v1/users/me/preferences/context`，按 Learning、Tools、Agent 消费方投影允许字段与契约元数据。
- Learning 与 Tools 前端只经 `users-api.js` 读取偏好；Learning 应用国内资源优先与外部资源显示策略，Tools 的最新区和分类区应用免费/国内优先，同时在 Users 不可用时降级为空偏好，保持公开内容可读。
- Agent 在服务端按当前认证用户读取 Users 偏好；请求 DTO 禁止客户端附带偏好副本，免费/国内优先影响工具排序，已启用偏好不再重复追问。
- 安全基线新增 `USR-SEC-011`，检查 Users facade、Agent 严格 DTO、前端适配器及无跨域用户表访问；当前结果为 10 pass、2 known-risk、0 fail。
- 验证证据：`.\scripts\verify-users.ps1` 通过，21 项 Users/Auth 单测和前端 facade/偏好适配测试通过；`.\scripts\verify-learning.ps1` 通过，33 项 Python 测试、2 项前端学习测试、104 条发布内容及性能检查通过。

## 2026-07-14 授权策略、审计规范与角色矩阵记录

- authorization 子域新增不可变授权上下文和纯权限判断；`AuthorizationService.require_permission` 统一返回 `PERMISSION_DENIED / 403`，并继续过滤已过期角色分配。
- 新增 FastAPI `require_permission` dependency；Agent chat 使用 `agent:chat`，认证后的用户学习状态使用 `learning:read`。公开 Learning/Tools 读取保持匿名可用，不依赖 Users 授权查询。
- 新增 Users/audit 子域，集中事件注册、元数据白名单、敏感键剔除和 SQLite append-only 写入；未知事件拒绝写入。
- 用户名、密码、密保、资料、头像、偏好、单会话撤销和退出其他设备已接入统一审计。账号类资源使用稳定 `user_uid`，单会话使用 `session_uid`，不记录密码、答案、令牌、Cookie、Authorization 或资料字段值。
- 审计规范见 `docs/users-audit-event-catalog.md`；IP 与 User-Agent 只从服务端请求上下文采集并限制长度。
- 单会话撤销现在校验受影响行；跨用户或不存在的 `session_uid` 返回 `SESSION_NOT_FOUND / 404`，不会修改其他用户会话，也不会写入成功审计。
- 新增普通用户、运营、管理员和过期审核员角色矩阵测试，覆盖允许/拒绝权限、稳定 API 403、过期分配失效、跨用户会话隔离、审计白名单、敏感值清除和真实命令写入。
- 安全基线新增 `USR-SEC-012` 与 `USR-SEC-013`；当前结果为 12 pass、2 known-risk、0 fail。
- 验证证据：`.\scripts\verify-users.ps1` 通过，24 项 Users/Auth 单测和前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，36 项 Python 测试、2 项前端测试、104 条发布内容及性能检查通过；Playwright 1440/768/390/360 四项通过。

## 2026-07-14 隐私同意、数据导出与账号生命周期记录

- 新增迁移 `006_user_privacy_lifecycle.sql`：append-only `user_privacy_consent_events` 保存同意类型、政策版本、grant/revoke、来源和时间；`user_data_requests` 保存导出与注销生命周期，并通过 partial unique index 限制每个用户只能有一个 pending/processing 注销申请。
- 隐私政策和 Agent memory 同意以最新事件为权威来源；旧 `user_preferences.agent_memory_enabled` 字段不再单独授权。Agent facade 只在最新事件为 granted 且政策版本等于当前服务端版本时返回 `agentMemoryEnabled=true`。
- 新增同意读取与 grant/revoke API；过期政策版本返回 `CONSENT_VERSION_OUTDATED / 409`。设置页偏好区的 Agent memory 开关已改用同意 API，隐私区可管理当前隐私政策同意。
- 数据导出需要当前密码重新验证，输出版本化 JSON，覆盖账号、资料、普通偏好、安全问题文本、会话展示信息、学习状态、收藏、同意事件和精简审计事实；不输出密码、答案、令牌、Cookie 或对应哈希。
- 注销生命周期为：默认 7 天等待期、软删除并撤销会话、默认 30 天恢复保留期、到期后由受控管理命令匿名化。等待期和保留期可分别通过 `AI_NAV_ACCOUNT_DELETION_GRACE_DAYS`、`AI_NAV_ACCOUNT_DELETION_RETENTION_DAYS` 配置。
- pending 申请只能由所属用户取消；execute/restore/anonymize 只接受稳定 `request_uid`，目标用户从服务端记录解析，并要求 `users:manage`。匿名化清理凭据、会话、密保、角色、私有学习状态和受管理头像，不删除公共 Learning/Tools 内容事实。
- 设置页新增“隐私与数据”分区，支持隐私政策状态、JSON 导出、注销申请、等待期展示和取消申请；敏感命令具有密码重验、确认与结果反馈。
- 生命周期与边界见 `docs/users-privacy-lifecycle.md`，新增隐私审计事件已同步到 `docs/users-audit-event-catalog.md`。
- 安全基线新增 `USR-SEC-014` 至 `USR-SEC-016`；当前结果为 15 pass、2 known-risk、0 fail。
- 验证证据：`.\scripts\verify-users.ps1` 通过，27 项 Users/Auth 单测和前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，39 项 Python 测试、2 项前端测试、104 条发布内容及性能检查通过。Playwright 1440/768/390/360 四项通过，桌面链路真实验证同意保存、导出内容排除认证秘密、注销申请与取消。

## 2026-07-14 用户资产与跨域 facade 记录

- 新增迁移 `007_user_workflow_assets.sql`，工作流与步骤使用稳定 UID；资产按用户隔离，幂等键按用户唯一，步骤只保存工具稳定 slug 和名称/链接快照，不通过级联外键绑定 Tools 生命周期。
- 新增 Users/assets 的 repository、service、facade 和薄 API，支持创建、分页读取、详情、乐观版本更新、归档、恢复及审计；旧 `/users/me/workflows` reserved 响应改为兼容读取真实资产。
- 下线或不存在的工具引用保留在原步骤中，返回 `target.status=unavailable` 和 `availability.status=degraded`，不静默删除用户数据；隐私导出包含已保存工作流，最终匿名化清理私人工作流。
- 新增 `UserContextFacade.for_agent()`，只向 Agent 投影偏好、能力布尔值和最小资产摘要。Agent chat 返回与 Users 保存 DTO 对齐的 `workflowDraft`，不读取用户资产表。
- Agent 保存命令要求 `sourceType=agent`、显式 `confirmed: true` 和 `Idempotency-Key`，并委托 Users command facade；重复幂等请求不重复创建或审计。
- 设置页工作流区改为真实列表，显示步骤数和 unavailable 状态，并通过确认对话框归档；前端 facade 增加列表、归档、恢复和 Agent 保存命令。
- 资产边界和 API 见 `docs/users-assets-contract.md`；新增四类资产审计事件并同步事件目录。`USR-501` 至 `USR-505` 全部完成。
- 安全基线新增 `USR-SEC-017` 至 `USR-SEC-019`，当前结果为 18 pass、2 known-risk、0 fail；已知风险仍仅为开发默认密钥和宽松 CORS。
- 验证证据：`.\scripts\verify-users.ps1` 通过，30 项 Users/Auth/Assets 单测及前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，42 项 Python 测试、2 项前端测试、104 条发布内容及性能检查通过。Playwright 1440/768/390/360 四项通过，桌面链路真实验证 unavailable 展示、确认归档和归档后移出活动列表。

## 2026-07-14 可观测性与发布收口记录

- 新增 Users/Auth 结构化访问日志中间件，覆盖 `/auth/*`、`/users/*` 与 Agent 工作流保存；响应返回安全 request ID 和 Server-Timing，日志字段固定为 requestId、路由 operation、status、latencyMs、errorCode，不读取请求体、身份字段、网络标识或认证秘密。
- 新增低基数进程内指标 registry 和管理员 `/users/operations/metrics` 接口，覆盖注册、登录、刷新、锁定、改密、单会话/其他会话撤销与 Agent 资产保存；5 分钟窗口提供登录失败、账号锁定、刷新、改密和撤销失败告警。
- 可观测性契约见 `docs/users-observability.md`；明确多 worker/多实例需接入集中式指标系统，且不得增加用户身份 label。
- 新增 `manage-users-backup.py`，通过 SQLite online backup 创建一致快照，执行 integrity/foreign-key 校验，恢复使用临时文件原子替换，覆盖前自动保留 pre-restore 副本。
- 新增 `rehearse-users-release.py` 和 `users-release-runbook.md`；临时库演练确认 7 个 migration checksum、源/备份/恢复完整性、外键及 canary 恢复全部通过，不触碰当前开发数据库。
- Users 性能基线升级为强制预算：登录、当前用户、刷新、资料、偏好、会话列表和资产列表共 7 条操作均通过 p95/SQL 语句数门禁；会话与资产列表的 2 条查询计划均命中预期索引。
- OpenAPI 冻结扩展到隐私、用户学习状态、资产、Agent 保存和管理员指标，共 46 条路径。最终验收脚本汇总 OpenAPI、数据库、前端、四视口、安全、性能与恢复演练，报告见 `docs/users-final-acceptance-report.md`。
- 安全基线新增 `USR-SEC-020` 至 `USR-SEC-022`，当前结果为 21 pass、2 known-risk、0 fail；已知部署风险仍为默认开发密钥和宽松 CORS，发布手册要求生产前处置。
- 验证证据：`.\scripts\verify-users.ps1` 全部通过，32 项 Users/Auth/Assets/Observability 单测通过；`.\scripts\verify-learning.ps1` 通过，44 项 Python 测试、2 项前端测试、104 条发布内容及性能检查通过；Playwright 1440/768/390/360 四项通过。`USR-601` 至 `USR-605` 全部完成。

## 2026-07-14 生产配置与部署探针加固记录

- 新增 `AI_NAV_ENV`、`AI_NAV_CORS_ALLOW_ORIGINS` 和 `AI_NAV_DATABASE_PATH`。本地开发保留明确的 localhost/127.0.0.1 allowlist；通配 origin 在所有环境均拒绝。
- `AI_NAV_ENV=production` 时，默认密钥或短于 32 位的密钥、非 Secure refresh Cookie 都会让应用快速启动失败；运行时子进程验证默认密钥退出码为 1。
- CORS methods、headers 和 exposed headers 改为显式白名单。最新实例验证允许 origin 的 preflight 返回 200 和精确 origin，未知 origin 返回 400 且没有许可头。
- 数据库初始化从模块导入阶段移入 FastAPI lifespan；测试和部署可通过 `AI_NAV_DATABASE_PATH` 注入数据库位置，OpenAPI 冻结不再隐式初始化数据库。
- 新增 `/api/v1/health/live` 与 `/api/v1/health/ready`。liveness 不访问依赖，readiness 验证数据库连接和全部 migration；数据库未准备时返回 `DATABASE_NOT_READY / 503`。
- 安全基线当前为 24 pass、0 known-risk、0 fail；最终验收包含 49 条冻结 OpenAPI 路径，原有默认密钥和宽松 CORS 两项部署风险已关闭。
- 验证证据：`.\scripts\verify-users.ps1` 全部通过，34 项 Users 测试通过；`.\scripts\verify-learning.ps1` 聚合验证 46 项 Python、2 项前端测试、104 条发布内容及性能检查；Playwright 1440/768/390/360 四项通过。最新开发实例为 `http://127.0.0.1:8091`。

## 2026-07-14 启动期兼容 DDL 正式迁移记录

- 新增 `008_user_auth_compatibility.sql`，正式管理旧库 `user_accounts.token_version` 补列及 `user_security_questions` 表/索引；启动函数中的特例 ALTER/CREATE 已全部移除。
- `apply_migrations` 改为在 `BEGIN IMMEDIATE` 锁内重新确认版本，逐语句执行 migration，并参数化写入版本/checksum；并发启动不会在锁外决定重复迁移。
- 新增受控 `ai-nav:add-column-if-missing` 指令，兼容旧库缺列和新 schema 已含列两种状态。表/列只接受合法标识符，列定义拒绝分号和注释语法。
- 新增迁移测试覆盖 checksum 漂移、旧/新 schema、重复执行、失败后列与版本原子回滚、恶意指令拒绝。启动期临时用户认证 DDL 的路线图事项已完成。
- 迁移/备份/恢复演练更新为 8 个 migration，源库、备份、恢复库 integrity 均为 `ok`，外键错误为 0，canary 与 checksum 全部一致。
- 安全基线新增 `USR-SEC-024`，当前为 25 pass、0 known-risk、0 fail。最终验收包含 49 条 OpenAPI 路径、8 个 migration、7 条性能预算和 2 条查询计划。
- 验证证据：`.\scripts\verify-users.ps1` 全部通过，34 项 Users 测试；`.\scripts\verify-learning.ps1` 通过，49 项 Python、2 项前端测试和 104 条发布内容；Playwright 4 个视口通过。真实开发库 readiness 为 `ready`、`migrationCount=8`，最新实例为 `http://127.0.0.1:8092`。

## 2026-07-14 认证限流、代理信任与自动刷新记录

- 新增 `009_auth_rate_limits.sql` 和 schema 镜像。固定窗口计数通过 `BEGIN IMMEDIATE + upsert` 原子持久化，主体只保存服务端 HMAC，不保存原始用户名、邮箱、IP、challenge UID 或 reset token；过期记录按 expiry 索引清理。
- 用户名探测、注册、登录、重置开始/密保验证/重置确认和 Token 刷新均接入 IP/主体组合限流；超过阈值返回 `AUTH_RATE_LIMITED / 429` 和 `Retry-After`，不会继续进入认证业务服务。
- 真实 HTTP 验证中，同一未知 identifier 前 10 次登录均返回统一 `INVALID_CREDENTIALS / 401`，第 11 次返回 `AUTH_RATE_LIMITED / 429`；数据库只出现长度 64 的哈希主体键。
- 默认不信任 `X-Forwarded-For`。仅当直连 peer 命中 `AI_NAV_TRUSTED_PROXY_CIDRS` 时才从右向左解析可信代理链；未信任直连或格式错误均使用直接连接地址。
- 前端统一 API client 新增 single-flight access-token refresh。并发 401 共享一个 HttpOnly Cookie refresh Promise，成功后原样重放一次请求，失败则清理本地 access 状态；上传请求使用相同边界。
- 路线图已根据代码和验证证据校准：Learning 5 项完成；Users/Auth 的服务拆分、学习状态/API、自动刷新、Cookie、限流、枚举/代理/会话安全项完成。“所有用户写操作统一审计、幂等和并发控制”仍保持未完成，等待逐命令审计而非笼统勾选。
- 安全基线新增 `USR-SEC-025`、`USR-SEC-026`，当前为 27 pass、0 known-risk、0 fail。性能门禁扩展为 8 条操作和 3 条查询计划，限流消费 p95/SQL 数及 expiry 索引均通过。

## 2026-07-14 Users 写命令安全收口记录

- 新增 `backend/app/users/command_safety.py`，对 33 条 Users/Auth/Agent 资产写命令逐条登记审计、重放防护和并发控制；登录、密码重置和 token 旋转使用限流、一次性令牌和状态机，不机械要求通用幂等键。
- 新增 `scripts/check-users-command-safety.py`，从 FastAPI 实际路由派生命令集合；漏登记、过期登记、空控制或未知审计事件都会使验证失败。
- 认证生命周期补充 7 类审计事件：注册、成功登录、密码重置开始/验证/完成、refresh 旋转和退出。只记录白名单摘要，不记录密码、答案、reset/refresh token 或请求体。
- 安全基线新增 `USR-SEC-027`；路线图 Users/Auth 5.3 最后一项已按风险等价保障收口。详细见 `docs/users-command-safety-matrix.md`。
- 验证证据：`.\scripts\verify-users.ps1` 全部通过，37 项 Users 测试和前端 facade 测试通过；`.\scripts\verify-learning.ps1` 通过，52 项 Python、2 项前端测试和 104 条发布内容；Playwright 1440/768/390/360 四项通过。真实开发库 readiness 为 `ready`、`migrationCount=9`，最新实例为 `http://127.0.0.1:8093`。
