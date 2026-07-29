# HTTP 子路径测试部署设计

> 用途：定义获批测试服务器上新旧项目共存、HTTP 测试环境、游客助手和真实 Provider 预览的边界；真实主机地址不进入仓库。
> 状态：设计已确认；任务 1–13 已实现，deterministic HTTP 实例已完成脱敏服务器验证。
> 日期：2026-07-29。
> 权威性：本文件约束后续实现计划；它不证明服务器已经部署、HTTPS 已配置或真实 Provider 已通过验收。

## 1. 目标与非目标

本次部署在一台 Ubuntu 22.04、2 vCPU、4 GiB、50 GiB 云服务器上完成以下目标：

- 根路径提供新旧项目选择页；
- 旧项目迁入 `/old-ai-nav/`，同时保持现有聊天能力；
- 新项目部署于 `/StarChart-AI/`；
- 新旧项目的进程、数据库、上传目录和发布目录相互隔离；
- HTTP 阶段只维护一个预置测试账号；
- 公网游客可体验离线助手、浏览器本地会话和工作流草案；
- 登录测试账号可体验个性资料、头像、学习状态、服务端会话和完整工作流管理；
- 真实 Provider 只通过 SSH 隧道连接的独立预览实例体验。

本次设计不包含以下事项：

- 不把 HTTP 测试环境宣称为生产发布；
- 不降低现有 `production` 配置的 HTTPS、Secure Cookie 和外部签收要求；
- 不公开测试账号凭据或真实 API Key；
- 不让公网游客调用真实 Provider；
- 不把旧项目数据复制到新项目测试库；
- 不伪造真实 Provider、容量、备份恢复、告警或生产回滚结果。

## 2. 已确认的服务器现状

当前 Nginx `server` 监听 80 端口，`server_name _`：

- `/` 从 `/opt/ai-nav2` 提供旧项目静态文件；
- `/chat` 反向代理到 `127.0.0.1:8000`；
- `/health` 反向代理到 `127.0.0.1:8000`；
- `/chat-widget.js` 从 `/opt/ai-nav2` 提供。

后续操作必须先备份现有站点配置，并保持旧项目的 8000 端口、聊天路由和文件目录可回滚。
迁移前还必须检查旧页面是否使用以 `/` 开头的静态资源 URL；如果存在，只为实际使用的旧资源配置显式兼容路由，不用一个宽泛的根路径回退覆盖项目选择页或新项目。

## 3. 目标拓扑

| 入口或资源 | 目标 | 暴露范围 |
| --- | --- | --- |
| `/` | `/var/www/project-hub/` 项目选择页 | 公网 |
| `/old-ai-nav/` | `/opt/ai-nav2/` 旧项目静态文件 | 公网 |
| `/chat`、`/health` | 旧服务 `127.0.0.1:8000` | 经 Nginx |
| `/chat-widget.js` | 旧项目脚本 | 公网 |
| `/StarChart-AI/` | 新项目 `127.0.0.1:8001` | 经 Nginx |
| `127.0.0.1:8002` | 真实 Provider 预览实例 | 仅 SSH 隧道 |

8001 和 8002 只能监听回环地址，不开放云安全组或主机防火墙公网端口。Nginx 是 8001 的唯一公网入口；8002 不配置 Nginx 路由。

服务器目录：

```text
/opt/starchart-ai/releases/<commit-sha>/
/opt/starchart-ai/current -> /opt/starchart-ai/releases/<commit-sha>/
/srv/starchart-ai-http-test/data/
/srv/starchart-ai-http-test/uploads/
/srv/starchart-ai-provider-preview/data/
/srv/starchart-ai-provider-preview/uploads/
/var/www/project-hub/
```

发布版本目录不可变；数据库、上传和日志位于源码树外。公网测试实例与 Provider 预览实例不共享 SQLite 文件。
两个实例也不共享 Unix 身份：公网实例使用 `starchart-ai-http-test`，预览实例使用
`starchart-ai-provider-preview`。各自数据目录为所属身份的 `0700`，环境文件为
`root:<对应专用组>` 的 `0640`；systemd 额外把对方的数据目录和环境文件设为不可访问。

只读预检有显式阶段契约：`before-first-start` 要求旧站 8000 已监听且 8001/8002
均未监听；`before-provider-preview` 要求 8000/8001 已监听且 8002 未监听。`ss`
命令退出成功但没有匹配行不等于端口已监听，预检必须解析匹配行。

## 4. URL 前缀契约

项目主体只增加通用、可配置的公开前缀能力，不硬编码服务器 IP 或 `/StarChart-AI`：

- 页面入口：`<public-base-path>/`；
- API：`<public-base-path>/api/v1`；
- 上传：`<public-base-path>/uploads`；
- 刷新 Cookie：`<public-base-path>/api/v1/auth`。

HTTP 测试覆盖层把 `public-base-path` 配置为 `/StarChart-AI`。Nginx 接收带前缀的公网请求，并将前缀剥离后转发到 8001；应用返回的同源 URL 和 Cookie Path 必须保留公开前缀。

必须为缺少尾斜杠的 `/StarChart-AI` 和 `/old-ai-nav` 提供稳定重定向。页面、API、上传、错误响应和刷新流程都必须经过前缀专项测试。

## 5. 部署覆盖层隔离

HTTP 专属配置进入独立覆盖层：

```text
deploy/http-test/
  env.example
  nginx/
  project-hub/
  scripts/
  systemd/
```

覆盖层允许包含无秘密的模板、部署脚本和项目选择页，不允许包含：

- 测试账号用户名或密码；
- 真实 API Key；
- 可用的服务端密钥；
- 真实数据库、上传文件、日志或备份；
- 服务器私钥或 SSH 配置。

项目主体的修改只用于通用能力，例如可配置公开前缀、有界游客上下文和可插拔部署策略。所有新增或修改文件必须登记到
`docs/00-index/http-test-deployment-file-index.md`。

## 6. HTTP 测试配置档

现有 `production` 配置继续要求 HTTPS，不为本次测试放宽。新增独立的 `http_test` 配置档，并在启动时强制验证：

- 至少 32 位随机服务端密钥；
- `AI_NAV_API_WORKERS=1`；
- 进程内 Agent 状态后端；
- 数据库和上传目录位于源码树外；
- `RESET_DATABASE_ON_START=0`；
- CORS 仅列出实际获批的 HTTP origin，并通过服务器 root-only 环境文件注入；
- Cookie Path 包含 `/StarChart-AI`；
- Provider 默认为离线确定性模式，实时开关关闭；
- 测试账号限制策略启用；
- 数据库、上传和发布目录不是旧项目目录。

HTTP 无法保护传输中的账号凭据与 Cookie。因此该环境只使用虚构测试数据，不承载真实个人信息；启用 HTTPS 后必须轮换或删除测试账号。

## 7. 测试账号能力边界

数据库中只维护一个预置普通测试账号，不授予管理员权限。账号由一次性管理命令创建，只保存密码哈希；凭据不得进入 Git、部署模板、文档、页面或日志。

允许：

- 登录、刷新会话和退出；
- 昵称、简介、头像与界面偏好；
- 学习进度、活动、收藏与最近阅读；
- 服务端短会话与长会话；
- 工作流创建、编辑、保存、归档与恢复；
- 查看自己的普通资料与会话。

服务端强制禁止：

- 注册其他账号；
- 修改用户名、密码、邮箱或手机号；
- 密码重置与账号恢复；
- 隐私同意修改、隐私导出、删除请求和匿名化；
- 删除唯一测试账号；
- 访问管理员接口。

前端隐藏或禁用受限入口只是体验优化，不能代替后端授权。直接调用受限 API 时返回稳定的
`403 DEMO_ACCOUNT_RESTRICTED`。

## 8. 助手能力与记忆

| 能力 | 公网游客 | 登录测试账号 | SSH Provider 预览 |
| --- | --- | --- | --- |
| 回答模式 | 离线确定性 | 离线确定性 | 真实 Provider |
| 工作流草案 | 浏览器本地生成与编辑 | 生成、编辑和保存 | 生成、编辑和保存 |
| 工作流归档/恢复 | 不允许 | 允许 | 允许 |
| 短会话 | 浏览器本地 | 公网测试库 | 独立预览库 |
| 长会话 | 浏览器本地 | 公网测试库 | 独立预览库 |
| Users 上下文 | 不读取 | 读取测试账号数据 | 读取预览测试账号数据 |

游客使用独立聊天入口，不伪造用户账号、不创建服务端会话、不写数据库。浏览器将有界的最近历史发送给服务端，使后续回答可以使用对话上下文。

游客本地存储边界暂定为：

- 最多 10 个会话；
- 每个会话最多 40 条消息；
- 最长保留 7 天；
- 超出限制时删除最旧内容；
- 提供“清除游客对话”入口；
- 不保存 Token、Cookie、账号资料或服务端工作流标识。

登录后不自动导入游客历史是暂定产品策略，后续可以重新评审；在正式修改该策略前，游客与账号数据保持隔离。

现有服务端会话能够保存消息，但后续实现必须补齐“有界历史上下文进入下一次 Agent 回答”的能力，避免把单纯的聊天记录展示误称为模型记忆。历史条数、总字符和单条长度必须有服务端上限。

## 9. 真实 Provider 预览

公网实例始终保持真实 Provider 关闭。真实模型体验使用另一个仅监听 `127.0.0.1:8002` 的实例：

- 只允许通过 SSH 本地端口转发访问；
- 使用独立数据库、上传目录和预置测试账号；
- API Key 通过服务器受限环境注入，不进入浏览器和仓库；
- 设置单请求、每日和每月成本上限；
- 保持全局并发、队列、超时、重试、回退和脱敏日志边界；
- 人工启动，体验结束后停止；
- 停止 8002 不影响公网 8001；
- 未完成外部签收和真实联网验证前，不宣称 Provider 已可生产发布。

后续实施或验收不得要求用户在聊天中粘贴真实 API Key。

## 10. 限流与滥用防护

公网游客入口至少需要：

- Nginx 按来源 IP 的请求速率与突发上限；
- 应用级全局并发、排队和请求超时；
- 请求体、消息历史、输出字符和工作流步骤上限；
- 不记录问题、回答、密码、Token、Cookie 或可识别账号内容；
- 游客不能使用账号数据、服务端会话或保存命令；
- Provider 无论配置是否错误，都不能被公网游客启用。

公网可访问不等于生产可用；HTTP 环境的结论始终是“测试候选”，不是“生产发布”。

## 11. 部署顺序

1. 完成通用源码、部署覆盖层、测试和文件索引。
2. 运行专项测试、全量质量门禁、发布包排除检查和秘密扫描。
3. 创建专用系统用户、发布目录和两个测试数据根目录。
4. 上传不可变发布包并建立 `current` 软链接。
5. 通过一次性命令分别初始化公网测试账号和 Provider 预览账号。
6. 启动 8001，先检查 loopback live/ready 探针。
7. 备份 Nginx 配置，安装项目选择页和新站点配置。
8. 执行 `nginx -t`；只有成功时才 reload。
9. 从公网验证根路径、旧项目、旧聊天和 `/StarChart-AI/`。
10. 通过 SSH 隧道人工启动并验证 8002；验证后停止。

服务器实际命令、操作人、时间和结果属于后续运行记录，不得提前写成已完成事实。

## 12. 验收

必须实际验证：

- `/` 项目选择页可达；
- `/old-ai-nav/` 页面、资源、`/chat`、`/health` 和 `/chat-widget.js` 正常；
- `/StarChart-AI/` 页面、静态资源、API、头像和 Cookie 路径正确；
- 游客可对话、维护本地会话、生成与编辑本地工作流草案；
- 游客无法写入服务器会话、账号或工作流数据；
- 测试账号允许的个性、头像、学习、会话和工作流能力通过；
- 测试账号受限身份、恢复、隐私和删除操作得到稳定 403；
- 8001、8002 不可从公网直接访问；
- SSH 预览实例能启动、调用、回退并停止，且无秘密泄漏；
- 全量 CI 与发布包门禁继续通过。

本地或 CI 通过不能替代服务器、外部 Provider、HTTPS、备份恢复和生产回滚验收。

## 13. 回滚

- Nginx：保留原配置；`nginx -t` 失败时不 reload。
- 应用：切回上一发布目录软链接并重启 8001。
- 数据：不执行破坏性 down migration，不删除故障库，先保留副本。
- 旧项目：8000、`/opt/ai-nav2` 和聊天兼容入口不随新项目回滚变化。
- Provider：停止 8002 即可与公网实例隔离。
- 文档：实际修改、验证和回滚结果同步写入专用文件索引及运行记录。

## 14. 文档与证据治理

专用入口为 `docs/00-index/http-test-deployment-file-index.md`。每个实现批次必须登记：

- 文件路径与职责；
- 修改原因；
- 当前状态；
- 专项测试与全量门禁；
- 服务器验证或未验证边界；
- 回滚方式；
- 对设计、运行手册和文档地图的影响。

文档不得包含测试账号凭据、真实 API Key、可用服务端密钥、Cookie、Token 或真实用户内容。

## 15. 实施对应表

| 设计边界 | 实现入口 | 验证入口 |
| --- | --- | --- |
| 独立 `http_test` / `provider_preview` 配置档、单 worker、外部持久化路径 | `backend/app/core/config.py`、`backend/run.py` | `tests/test_http_test_runtime.py`、`tests/test_agent_provider.py` |
| `/StarChart-AI` 公共前缀与公开能力 | `frontend/assets/js/public-path.js`、`backend/app/api/v1/routers/common.py` | `tests/test_public_path.mjs`、`tests/test_http_test_runtime.py` |
| 唯一测试账号及受限身份、恢复、隐私和删除动作 | `backend/app/users/deployment_policy.py`、`backend/app/api/v1/dependencies/deployment_policy.py` | `tests/test_http_test_policy.py` |
| 登录会话有界历史与并发 replay 一致性 | `backend/app/agent/sessions.py`、`backend/app/agent/replay.py`、`backend/app/api/v1/routers/agent.py` | `tests/test_agent_sessions.py`、`tests/test_agent_replay.py` |
| 游客无账号、无数据库副作用的确定性入口 | `backend/app/api/v1/routers/agent.py` | `tests/test_agent_guest.py` |
| 游客浏览器记忆与身份切换隔离 | `frontend/assets/js/guest-agent-memory.js`、`frontend/assets/js/assistant-session-epoch.js`、`frontend/assets/js/assistant-page.js` | `tests/test_guest_agent_memory.mjs`、`tests/test_auth_ui.mjs` |
| 无命令行秘密的唯一账号初始化 | `scripts/provision-http-test-account.py` | `tests/test_http_test_account_provisioning.py` |
| Nginx、systemd、数据目录和环境模板覆盖层 | `deploy/http-test/` | `tests/test_http_test_overlay.py` |
| deny-first 发布包 | `scripts/build-release-package.ps1` | `tests/test_release_http_test_overlay.py` |
| 专项门禁、秘密扫描和无秘密 manifest | `scripts/verify-http-test-deployment.ps1`、`scripts/check-no-secrets.py` | `docs/06-evidence/platform/http-test-deployment-manifest.json` |
| 服务器安装与验证 | `docs/04-operations/deployment/http-test-deployment-runbook.md` | `docs/06-evidence/platform/http-test-server-validation.json`；deterministic HTTP 实例 `GO` |
| 停止、恢复与回滚演练 | `docs/04-operations/deployment/http-test-deployment-runbook.md` | 当前 `NOT RUN`，不得由安装成功推断 |

当前脱敏证据只证明 deterministic HTTP 实例已验证，不证明真实 Provider、HTTPS、备份恢复或回滚通过。当前运行事实以
`docs/00-index/http-test-deployment-file-index.md` 和机器证据为准。
