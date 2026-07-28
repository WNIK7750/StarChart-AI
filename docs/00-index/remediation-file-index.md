# 全项目审计整改文件索引

> 版本：2026-07-28
> 用途：为新的整改对话提供问题、实现、测试、脚本和文档之间的稳定导航。  
> 整改提示词：`docs/07-prompts/audits/full-project-remediation-prompt.md`  
> 独立复验提示词：`docs/07-prompts/audits/full-project-remediation-verification-prompt.md`  
> 独立复验报告：`docs/05-quality/audits/full-project-remediation-verification-report.md`  
> Git 提交执行交接：`docs/05-quality/audits/git-commit-readiness-handoff.md`  
> 权威问题状态：`docs/05-quality/audits/full-project-remediation-verification-report.md`

## 1. 新对话最小阅读集

新对话必须先按以下顺序阅读，避免根据旧路径或历史规划猜测当前状态：

1. `docs/00-index/remediation-file-index.md`
2. `docs/05-quality/audits/full-project-remediation-verification-report.md`
3. `docs/00-index/http-test-deployment-file-index.md`（HTTP 测试部署与服务器证据）
4. `docs/05-quality/audits/git-commit-readiness-handoff.md`（执行 Git 提交时使用）
5. `docs/05-quality/audits/full-project-reaudit-report.md`
6. `docs/05-quality/audits/full-project-audit-report.md`
7. `docs/01-overview/fullstack-development-results-handoff.md`
8. `docs/00-index/documentation-map.md`
9. `docs/02-architecture/modular-monolith-guidelines.md`
10. `docs/07-prompts/audits/full-project-remediation-prompt.md`
11. `docs/07-prompts/audits/full-project-remediation-verification-prompt.md`（复验对话使用）

读取完成后，再检查 `git status --short`、`git diff --stat` 和实际文件树。索引只负责导航；如果索引与当前代码冲突，以当前代码、迁移和自动化测试为准，并同步修正索引。

## 2. 整改状态索引

| 批次 | 审计编号 | 当前状态 | 主要入口 |
| ---: | --- | --- | --- |
| 1 | AUD-SEC-001A / AUD-SEC-001B | 已修复（真实发送服务外部阻塞） | Auth Router、authentication service/repository、Users 测试 |
| 2 | AUD-CFG-001 | 已修复 | core config、数据库初始化、配置模板 |
| 3 | AUD-SCA-001 | 已修复 | requirements、头像处理、静态文件挂载、依赖审计 |
| 4 | AUD-WEB-002 | 已修复 | app middleware、HTML/API 响应测试 |
| 4 | AUD-AUTH-002 | 已修复 | frontend API、Auth UI、refresh/session 服务 |
| 4 | AUD-API-002 | 已修复 / 独立复验通过 | 84 个 JSON 操作全部使用字段级响应模型；宽泛 `JsonObject` 归零 |
| 5 | AUD-CI-002 / AUD-CI-003 | 已修复 | GitHub workflow、验证脚本、覆盖率和 SCA |
| 6 | AUD-TEST-004 | 已修复 | user_learning/privacy/learning Routers、access middleware |
| 6 | AUD-CODE-003 | 已修复 | Ruff 核心规则 0 命中 |
| 6 | AUD-DB-004 | 已修复 | `backend/app/db/database.py` |
| 6 | AUD-REP-003 | 已修复 | `.gitignore`、发布与备份脚本 |
| 7 | AUD-OPS-002 | 部分验证：deterministic HTTP 测试部署 GO；生产仍为外部阻塞 / NO-GO | HTTP 部署索引与服务器证据；Provider、HTTPS、容量、恢复、回滚和生产签收文档 |

新对话每完成一个批次，应把“当前状态”更新为“修复、部分修复或外部阻塞”，并在整改报告中写入测试证据。

独立本地复验及后续整改已完成：176/176 Python、34/34 Node、36/36 JavaScript
语法、Python `compileall`、Ruff、依赖审计、85.9% 分支模式覆盖率、数据库校验和
347 文件发布 allowlist 均通过。`AUD-API-002` 的 44 个宽泛模型已替换为字段级 DTO，
服务层额外内部字段会在 HTTP 序列化前过滤。本地整改候选通过；权威数字、差异和生产
NO-GO 条件见
`docs/05-quality/audits/full-project-remediation-verification-report.md`。

## 3. 批次 1：账户恢复

### 实现入口

- `backend/app/api/v1/routers/auth.py`
- `backend/app/users/authentication/service.py`
- `backend/app/users/authentication/ports.py`
- `backend/app/users/authentication/repositories/sqlite.py`
- `backend/app/users/authentication/rate_limit.py`
- `backend/app/users/authentication/recovery.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/schemas.py`

### 相关数据与迁移

- `database/migrations/`
- `backend/app/db/database.py`

如果新增恢复令牌表或发送端口，必须使用新的顺序迁移，不直接重写已执行迁移。

### 测试入口

- `tests/test_users_services.py`
- `tests/test_auth_ui.mjs`
- `tests/test_frontend_api.mjs`
- `tests/fixtures/`
- `docs/06-evidence/users/password_recovery_remediation.json`

### 同步文档

- `docs/03-domains/users/user-module-design.md`
- `docs/03-domains/users/users-auth-rate-limits.md`
- `docs/03-domains/users/users-audit-event-catalog.md`
- `docs/04-operations/users/users-release-runbook.md`

## 4. 批次 2：生产配置

### 实现入口

- `backend/app/core/config.py`
- `backend/app/db/database.py`
- `backend/app/main.py`
- `backend/run.py`
- `.env.example`
- `production.env.example`

### 测试和验证

- `tests/test_users_services.py`
- `tests/test_agent_provider.py`
- `tests/test_agent_runtime.py`
- `scripts/verify-foundation.ps1`
- `scripts/verify-agent.ps1`
- `scripts/python-runtime.ps1`
- `docs/06-evidence/platform/production_config_remediation.json`

### 同步文档

- `README.md`
- `docs/01-overview/fullstack-development-results-handoff.md`
- `docs/04-operations/agent/`
- `docs/04-operations/users/users-release-runbook.md`

## 5. 批次 3：依赖、头像与静态文件

### 依赖与应用装配

- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/run.py`

### 上传和图片处理

- `backend/app/api/v1/routers/users.py`
- `backend/app/users/profile/avatar.py`
- `backend/app/users/profile/service.py`
- `backend/app/users/profile/repositories/sqlite.py`

### 测试和脚本

- `tests/test_users_services.py`
- `scripts/check-users-security-baseline.py`
- `scripts/verify-users.ps1`
- `scripts/verify-foundation.ps1`
- `scripts/verify-agent.ps1`

### 证据与文档

- `docs/05-quality/audits/full-project-audit-report.md`
- `docs/05-quality/audits/full-project-reaudit-report.md`
- `docs/06-evidence/users/users_security_baseline.json`
- `docs/06-evidence/platform/dependency_input_remediation.json`

## 6. 批次 4：Web 安全、令牌和响应模型

### 安全响应头

- `backend/app/main.py`
- `backend/app/api/v1/routers/common.py`
- `backend/run.py`
- `frontend/`

### Access Token 和 refresh 流程

- `frontend/assets/js/api.js`
- `frontend/assets/js/auth-local-state.js`
- `frontend/assets/js/auth-ui.js`
- `frontend/assets/js/settings.js`
- `backend/app/api/v1/routers/auth.py`
- `backend/app/users/authentication/service.py`
- `backend/app/users/security/service.py`
- `backend/app/users/security/repositories/sqlite.py`

### 响应模型

- `backend/app/api/v1/routers/`
- `backend/app/api/v1/schemas.py`
- `backend/app/agent/schemas.py`
- `backend/app/learning/schemas.py`
- `backend/app/tools/`
- `backend/app/users/`

### 测试和证据

- `tests/test_frontend_api.mjs`
- `tests/test_auth_ui.mjs`
- `tests/test_users_frontend.mjs`
- `tests/test_users_services.py`
- `tests/test_agent_frontend.mjs`
- `docs/06-evidence/users/auth_users_openapi.json`
- `docs/06-evidence/users/auth_users_response_shapes.json`
- `scripts/freeze-users-contracts.py`
- `docs/06-evidence/platform/web_token_response_remediation.json`

## 7. 批次 5：CI 和质量门禁

工作流位于当前工作区的父级 Git 仓库目录：

- `../.github/workflows/ai-nav-foundation-ci.yml`

本地门禁：

- `scripts/verify-foundation.ps1`
- `scripts/verify-frontend.ps1`
- `scripts/verify-learning.ps1`
- `scripts/verify-tools.ps1`
- `scripts/verify-users.ps1`
- `scripts/verify-agent.ps1`
- `scripts/check-users-command-safety.py`
- `scripts/check-users-security-baseline.py`

相关配置：

- `backend/requirements.txt`
- `.gitignore`
- `backend/requirements-dev.txt`
- `pyproject.toml`
- `.coveragerc`
- `scripts/verify-quality.ps1`
- `docs/06-evidence/platform/ci_quality_remediation.json`

新增 CI 依赖前，先确认其锁定方式、Python 3.12/Windows 支持和失败策略。

## 8. 批次 6：边界覆盖和工程问题

### HTTP/ASGI 边界

- `backend/app/api/v1/routers/user_learning.py`
- `backend/app/api/v1/routers/privacy.py`
- `backend/app/api/v1/routers/learning.py`
- `backend/app/users/observability/access.py`
- `backend/app/users/observability/metrics.py`
- `backend/app/platform/navigation.py`
- `backend/app/main.py`

### 所属服务和 repository

- `backend/app/users/learning_state/`
- `backend/app/users/privacy/`
- `backend/app/learning/`
- `backend/app/platform/`

### 当前 Ruff 命中

- `backend/app/agent/tools/learning_tools.py`
- `backend/app/users/assets/service.py`
- `scripts/check-users-security-baseline.py`
- `scripts/serve-agent-stage5-acceptance.py`

### 数据库资源生命周期

- `backend/app/db/database.py`
- `database/migrations/`
- `tests/test_http_boundaries.py`
- `scripts/build-release-package.ps1`
- `docs/06-evidence/platform/boundary_engineering_remediation.json`

### 测试入口

- `tests/test_users_services.py`
- `tests/test_learning_services.py`
- `tests/test_agent_services.py`
- `tests/test_agent_observability.py`

新增边界测试可以放入已有所属测试文件；如果文件职责已经过重，可以创建明确命名的 ASGI/Router 集成测试文件，避免继续堆入超大测试文件。

## 9. 批次 7：外部生产签收

### Provider 与 Agent 运维

- `backend/app/agent/providers/`
- `backend/app/agent/governance.py`
- `backend/app/agent/observability.py`
- `backend/app/agent/runtime.py`
- `docs/04-operations/agent/`
- `docs/06-evidence/agent/`

### Users、备份与恢复

- `scripts/manage-users-backup.py`
- `scripts/rehearse-users-release.py`
- `docs/04-operations/users/users-release-runbook.md`
- `docs/06-evidence/users/`
- `docs/04-operations/production-external-signoff-checklist.md`

### 外部阻塞记录

没有真实环境或授权时，只更新：

- `docs/05-quality/audits/full-project-remediation-report.md`
- `docs/05-quality/audits/full-project-remediation-verification-report.md`
- 对应运行手册中的待签收清单。

不得生成伪造的成功 JSON、容量数字、合规结论或 Provider 验收结果。

## 10. 全量验证索引

### Python

- `tests/test_*.py`
- `scripts/verify-foundation.ps1`
- `scripts/verify-agent.ps1`

### Frontend

- `tests/test_*.mjs`
- `scripts/verify-frontend.ps1`

### 数据、契约和生成物

- `database/migrations/`
- `docs/06-evidence/`
- `scripts/freeze-users-contracts.py`
- `scripts/build-users-acceptance-report.py`
- `scripts/build-agent-evaluation-manifest.py`
- `scripts/build-agent-blind-protocol-manifest.py`

### 最终同步

- `docs/05-quality/audits/full-project-remediation-report.md`
- `docs/05-quality/audits/full-project-reaudit-report.md`
- `docs/00-index/remediation-file-index.md`
- `docs/00-index/documentation-map.md`
- `docs/01-overview/fullstack-development-results-handoff.md`
- `README.md`

## 11. 索引维护规则

- 文件移动、新增迁移、新增脚本或拆分测试时，同一批次内更新本索引；
- 不在索引中复制大段实现细节，只记录稳定入口和所有权；
- 已关闭问题仍保留原编号和历史入口，状态改为“已修复”；
- 被证伪的问题标为“误报”，同时保留证伪测试路径；
- 外部问题标为“外部阻塞”，不得伪装成本地已修复；
- 每次最终交接前检查索引中的显式路径都真实存在。
