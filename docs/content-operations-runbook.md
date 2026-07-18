# 内容维护、发布与链接巡检手册

更新时间：2026-07-15

## 1. 边界与事实源

内容治理是模块化单体内的运维流程，不是独立服务：

- Learning 拥有学习节点、主资料、章节和补充链接；内容输入集中在 `database/learning_content.sql`。
- Tools 拥有工具、分类、展示位和官网链接；前端工具快照只作为迁移生成输入，数据库是唯一运行事实源。
- Users 只拥有用户状态和资产，不修改公共内容事实。
- Agent 保持冻结；未来只能读取 Learning/Tools 已发布事实和链接状态。

## 2. 生命周期

Learning 与 Tools 的公开内容统一使用 `draft -> published -> archived`：

- `draft`：可在迁移或维护分支中校验，不进入公开 API。
- `published`：进入公开 API；链接状态可以是 `unchecked/healthy/degraded/unavailable`。
- `archived`：停止公开读取，但保留稳定 UID/slug 和历史数据，不物理删除。

`degraded` 表示站点可达但存在鉴权、限流、不支持探测或瞬时网络/服务错误；只有明确的永久客户端错误才记为 `unavailable`，并在前端禁用外跳、显示维护状态。链接状态不替代发布状态。

## 3. 发布流程

1. 发布前备份并验证整个 SQLite 数据库：

```powershell
python scripts/manage-users-backup.py backup --source database/ai_nav.sqlite3 --output backups/ai_nav-pre-content-release.sqlite3
python scripts/manage-users-backup.py verify --database backups/ai_nav-pre-content-release.sqlite3
```

2. 修改内容输入并生成追加迁移。已执行迁移不可改写；Tools 目录使用生成器输出更高版本迁移。
3. 在临时数据库演练 schema、seed、`learning_content.sql` 和全部迁移。
4. 执行不联网的发布结构门禁：

```powershell
python scripts/check-content-links.py
```

5. 在允许联网的维护环境先预览巡检结果，再经人工确认写回：

```powershell
python scripts/check-content-links.py --online --timeout 6 --workers 8
python scripts/check-content-links.py --online --write --timeout 6 --workers 8
```

6. 对 `unavailable` 逐条复核。确认下线时用追加迁移改为 `archived`；替换链接时保留稳定 UID/slug 并递增内容版本。
7. 运行 `verify-foundation.ps1` 后再发布；失败时再单独运行对应模块脚本定位。

## 4. 回滚

- 代码或静态资源异常：回滚应用版本，数据库迁移保持向前兼容，不删除迁移记录。
- 内容误发布：用新的追加迁移恢复旧字段或将目标归档，不改写历史迁移。
- 数据损坏：停止写入，验证发布前备份，再用 `manage-users-backup.py restore --replace` 原子恢复；命令会先保留 pre-restore 副本。
- 恢复后检查 readiness、迁移 checksum、外键、104 条 Learning 引用、134 条公开 Tools 链接和页面关键流程。

## 5. 维护节奏

- 内容发布前必须运行离线门禁。
- 外链巡检按发布批次执行；第三方网络不稳定时不自动归档，由维护人员复核。
- `last_checked_at/last_verified_at` 只由显式 `--online --write` 更新，普通启动和 CI 不访问第三方网站。
- 归档内容保留稳定标识，保证用户历史记录和已保存工作流仍可解释。
