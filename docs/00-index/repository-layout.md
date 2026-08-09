# 仓库目录与文件权威规则

> 状态：当前有效
> 更新日期：2026-08-09
> 用途：明确唯一源码入口、本地生成物边界和 HTTPS 发布所需文件，避免旧副本或历史产物被误用。

## 1. 唯一有效目录

| 路径 | 职责 | 是否进入发布包 |
| --- | --- | --- |
| `backend/` | FastAPI 应用、领域服务和运行入口 | 是 |
| `frontend/` | 唯一前端源码；页面、样式、脚本和静态资源 | 是 |
| `database/` | 初始结构、种子数据和按编号追加的迁移 | 仅结构、种子与迁移 |
| `deploy/http-test/` | 隔离 HTTP 测试环境覆盖层 | 按发布清单 |
| `deploy/production/` | HTTPS 生产环境的 Nginx、systemd、脚本和唯一生产配置模板 | 是 |
| `scripts/` | 验证、数据维护、备份和发布包构建工具 | 仅发布运行所需脚本 |
| `tests/` | Python 与前端契约测试 | 否 |
| `docs/` | 当前设计、运维手册、质量结论、证据和历史快照 | 仅 `04-operations/` |
| `.github/` | CI 配置 | 否 |

仓库根目录只保留跨模块入口和项目级配置，例如 `README.md`、`start.ps1`、
`.env.example`、`pyproject.toml` 和 Git 配置文件。不得在根目录再创建第二套前端、
后端、部署配置或“最新版”副本。

## 2. 权威性规则

1. 前端只有 `frontend/` 一个来源；任何“副本”“备份”“旧版”目录都不得参与启动、测试或发布。
2. 生产配置模板只有 `deploy/production/env.example`；真实配置保存在服务器
   `/etc/starchart-ai/production.env`，不写入仓库。
3. 生产发布只通过 `scripts/build-release-package.ps1` 的允许清单选取文件，不能直接压缩整个工作区。
4. 数据库迁移只追加到 `database/migrations/`，已应用迁移不得重命名或修改。
5. 当前事实以代码、迁移和自动化测试为先；`docs/05-quality/analysis/` 中带日期的目录是历史快照，不是运行入口。
6. 用户 API Key 不进入 SQLite、环境模板、日志、发布包或文档；生产环境必须接入独立凭据存储后才能启用用户模型。

## 3. 仅本地存在的内容

以下路径不属于源码，已由 `.gitignore` 排除：

- `.env`、`.venv/`、IDE 状态；
- `database/*.sqlite3*`、`uploads/`；
- `.pytest_cache/`、`.ruff_cache/`、`.coverage`、`test-results/`；
- `*.log`、`.tmp_*.txt`；
- `release/` 中的发布压缩包；
- `.repo-backups/` 中的恢复 bundle。

其中 `.repo-backups/` 是仓库迁移恢复资料，不作为程序使用，也不应在发布前随意删除。
发布压缩包、测试输出、日志和缓存均可重新生成，不得作为“当前版本”依据。

## 4. HTTPS 上线边界

生产机器应保持以下分离：

```text
/opt/starchart-ai/current/                 只读应用发布内容
/srv/starchart-ai-production/data/         SQLite 持久数据
/srv/starchart-ai-production/uploads/      用户上传
/etc/starchart-ai/production.env           仅服务器可读的运行配置
/var/backups/starchart-ai-production/      独立备份
Nginx :443                                 TLS 终止与反向代理
FastAPI 127.0.0.1:8003                     非公网应用监听
```

HTTPS 由 Nginx 终止并转发到 loopback FastAPI；证书申请、续期和代理头信任必须按
`docs/04-operations/deployment/https-production-deployment-runbook.md` 执行。用户模型
功能还要求独立 Secret Manager/凭据存储适配器；当前 Linux 生产模板保持
`AI_NAV_AGENT_CREDENTIAL_STORE=unconfigured`，因此在适配器完成前应失败关闭。

## 5. 整理和发布前验证

```powershell
.\scripts\verify-repository-layout.ps1
.\scripts\verify-production-deployment.ps1
```

第一个命令检查唯一入口、迁移编号、重复生产模板和已跟踪运行产物；第二个命令验证
生产覆盖层、发布允许清单、密钥扫描和 Git 空白错误。生成发布包时必须显式指定新文件名，
不得复用历史 ZIP。
