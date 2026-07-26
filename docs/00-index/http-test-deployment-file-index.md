# HTTP 测试部署文件索引

> 用途：作为 HTTP 子路径测试部署的文件路由、实现进度、验证证据和回滚同步入口。
> 状态：设计与实施计划已完成；任务 1 运行时配置档和任务 2 公开运行能力/公共路径投影已完成；部署覆盖层和服务器尚未修改。
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

当前没有应用源码、测试、部署模板、Nginx、systemd、数据库或服务器文件被本设计阶段修改。

## 3. 实现候选路由

下表由实施计划复核后用于约束下一阶段实现，不表示文件已经修改。每次修改后必须更新状态。

| 候选范围 | 预期职责 | 当前状态 |
| --- | --- | --- |
| `backend/app/core/config.py` | 通用公开前缀与独立 `http_test` 配置验证 | 候选，未修改 |
| `backend/app/main.py` | 复核 Nginx 剥离前缀后是否需要改动 | 已复核，无需修改；内部路径保持 `/api/v1`、`/uploads` 和 `/` |
| `backend/app/api/v1/routers/agent.py` | 游客聊天入口与有界历史上下文 | 候选，未修改 |
| `backend/app/agent/schemas.py` | 严格的游客历史请求契约 | 候选，未修改 |
| `frontend/assets/js/api.js` | 前缀感知的 API URL | 候选，未修改 |
| `frontend/assets/js/assistant-page.js` | 游客本地会话、草案和登录能力切换 | 候选，未修改 |
| `frontend/assistant.html` | 游客状态与清除入口 | 候选，未修改 |
| Users 授权与命令边界 | 唯一测试账号的身份、恢复、隐私和删除限制 | 候选，精确文件待实现计划复核 |
| `tests/` | 前缀、游客助手、测试账号限制和无服务端写入回归 | 候选，未修改 |
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
- 实施计划：已完成，共 13 个顺序任务；任务 1 和任务 2 已完成，其余任务尚未执行。
- 应用实现：任务 1 的运行时配置档、任务 2 的公开运行能力与公共路径投影已完成；其余应用功能尚未开始。
- 部署覆盖层：未创建。
- 本地专项测试：任务 1 和任务 2 已运行并通过；其余专项测试未运行。
- 全量门禁：未因本设计重新运行。
- 服务器部署：未执行。
- HTTP 测试候选：`NO-GO`，仍等待后续功能、部署覆盖层和服务器验证。
- 生产发布：`NO-GO`，HTTPS、外部签收和生产证据仍缺失。
