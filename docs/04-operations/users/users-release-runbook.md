# Users 发布、备份与回滚手册

Agent 阶段 1 的生产拓扑固定为 `AI_NAV_API_WORKERS=1` 与
`AI_NAV_AGENT_RUNTIME_STATE_BACKEND=process_local`，使用
`python backend/run.py` 启动。多 worker 或未实现的共享状态后端会在启动时失败；
扩容触发条件见 `docs/02-architecture/decisions/adr-agent-runtime-topology.md`。
跨 Provider、恢复发送端、容量、生产恢复、回滚与告警的最终责任签收见
`docs/04-operations/production-external-signoff-checklist.md`；未全部签收时保持 NO-GO。

## 发布前

1. 冻结写入窗口，确认没有长事务或正在执行的匿名化任务。
2. 以 `deploy/production/env.example` 为唯一无密钥契约：设置 `AI_NAV_ENV=production`、至少 32 位随机 `AI_NAV_SECRET_KEY`、明确的 HTTPS `AI_NAV_CORS_ALLOW_ORIGINS`、源码树外的 `AI_NAV_DATABASE_PATH`/`AI_NAV_UPLOAD_DIR`，并启用 `AI_NAV_REFRESH_COOKIE_SECURE=1`、保持 `RESET_DATABASE_ON_START=0`；仅在反向代理部署时按真实网段设置 `AI_NAV_TRUSTED_PROXY_CIDRS`。不安全组合会在启动时失败。
3. 密码恢复默认使用禁用发送端并 fail-closed。发布负责人必须选择并接入真实的已验证邮件或短信服务，完成数据处理、域名/号码、退信、限流和安全通知签收；在此之前公开开始接口只返回统一受理文案，不会实际发送，也不得宣称“邮件已发送”。
4. 执行 `.\scripts\verify-foundation.ps1` 和归档中的 Playwright 视口验收；失败时再单独运行对应模块脚本定位。
5. 执行 `python scripts/rehearse-users-release.py`，要求迁移 checksum、完整性、外键和恢复 canary 全部通过。
6. 创建在线一致备份：

```powershell
python scripts/manage-users-backup.py backup --source database/ai_nav.sqlite3 --output backups/ai_nav-pre-release.sqlite3
python scripts/manage-users-backup.py verify --database backups/ai_nav-pre-release.sqlite3
```

## 发布

1. 先部署兼容旧前端的后端和增量迁移，再发布静态资源。
2. 启动时只允许 `apply_migrations` 执行未应用 migration；禁止修改已应用 SQL，checksum 不一致必须中止。
3. 检查 `/api/v1/health/live` 与 `/api/v1/health/ready`、注册/登录/刷新、当前用户、设置页、Learning 公共读取和工作流列表。
4. 使用管理员账号检查 `/api/v1/users/operations/metrics`；普通用户必须得到稳定 403。
5. 观察至少一个告警窗口，确认 5xx、登录失败、锁定和刷新失败没有异常抬升。

## 应用回滚

- 当前迁移均为向后兼容的增量表/列；优先回滚应用版本并保留新字段，不执行破坏性 down migration。
- Refresh Token 只通过 HttpOnly Cookie 签发和轮换，JSON 响应不再返回 body token；
  客户端回滚不得恢复 localStorage token。
- Agent 仅经 Users facade 保存工作流，回滚 Agent 不影响已保存资产结构。

## 迁移编写约束

- 常规 DDL/DML 直接写入按编号排序的 `.sql` 文件，每个文件在 `BEGIN IMMEDIATE` 锁内逐语句执行并原子写入版本/checksum。
- 兼容旧库补列时可使用单行指令：`-- ai-nav:add-column-if-missing <table> <column> <definition>`。表名和列名仅允许 SQL 标识符字符，definition 禁止分号和内联注释。
- 指令只用于新 schema 已含列、旧 schema 仍缺列的过渡场景；新表继续使用 `CREATE TABLE IF NOT EXISTS`。
- migration 失败时列变更、后续语句和版本记录必须一起回滚；不得把兼容 ALTER/CREATE 重新放回应用启动函数。

## 数据库恢复

1. 停止应用写入并保留故障库副本。
2. 校验目标备份，然后执行原子恢复；`--replace` 会先创建带 UTC 时间戳的 pre-restore 副本：

```powershell
python scripts/manage-users-backup.py verify --database backups/ai_nav-pre-release.sqlite3
python scripts/manage-users-backup.py restore --backup backups/ai_nav-pre-release.sqlite3 --target database/ai_nav.sqlite3 --replace
```

3. 重新执行完整性、外键、迁移 checksum 和关键 API smoke test。
4. 恢复写入后检查 Users 指标；若异常，停止写入并恢复自动生成的 pre-restore 副本。

## 发布后检查单

- OpenAPI 已冻结，资产与 Agent 保存端点存在。
- 密码恢复存在/不存在账号响应不可区分；一次性凭据、过期、重放、篡改、会话撤销专项通过；真实发送端仍需单独外部签收。
- 安全基线 `fail=0`，生产部署风险已显式处置。
- 性能预算和慢查询计划全部通过。
- 桌面、平板、移动四视口无溢出和未知 console error。
- 备份可验证、可恢复，canary 与所有迁移 checksum 一致。
- 日志不包含用户名、邮箱、请求体、Authorization、Cookie、令牌、密码或安全答案。
- HTML、API、错误和静态资源均有 CSP、nosniff、Referrer、frame 与 Permissions
  响应头；HSTS 只有在生产 HTTPS 终止已确认并设置 `AI_NAV_HTTPS_CONFIRMED=1`
  后启用。
- 发布归档只使用 `scripts/build-release-package.ps1` 的 allowlist 选择；先以
  `-ValidateOnly` 确认日志、前端副本、覆盖率、数据库、上传与本地运行产物均为 0。
