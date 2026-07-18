# Users 发布、备份与回滚手册

## 发布前

1. 冻结写入窗口，确认没有长事务或正在执行的匿名化任务。
2. 设置 `AI_NAV_ENV=production`、至少 32 位随机 `AI_NAV_SECRET_KEY`、明确的 `AI_NAV_CORS_ALLOW_ORIGINS`，并在 HTTPS 下启用 `AI_NAV_REFRESH_COOKIE_SECURE=1`；仅在反向代理部署时按真实网段设置 `AI_NAV_TRUSTED_PROXY_CIDRS`。不安全配置会在启动时失败。
3. 执行 `.\scripts\verify-foundation.ps1` 和归档中的 Playwright 视口验收；失败时再单独运行对应模块脚本定位。
4. 执行 `python scripts/rehearse-users-release.py`，要求迁移 checksum、完整性、外键和恢复 canary 全部通过。
5. 创建在线一致备份：

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
- Refresh Cookie 仍保留 body token 兼容期，必要时可回滚客户端而不回滚会话表。
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
- 安全基线 `fail=0`，生产部署风险已显式处置。
- 性能预算和慢查询计划全部通过。
- 桌面、平板、移动四视口无溢出和未知 console error。
- 备份可验证、可恢复，canary 与所有迁移 checksum 一致。
- 日志不包含用户名、邮箱、请求体、Authorization、Cookie、令牌、密码或安全答案。
