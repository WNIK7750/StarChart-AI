# HTTP 测试部署文件索引

> 用途：作为 HTTP 子路径测试部署的文件路由、实现进度、验证证据和回滚同步入口。
> 状态：设计与实施计划已完成；应用源码、部署覆盖层和服务器尚未修改。
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
- 实施计划：已完成，共 13 个顺序任务；尚未执行计划内测试或修改应用。
- 应用实现：未开始。
- 部署覆盖层：未创建。
- 本地专项测试：未运行。
- 全量门禁：未因本设计重新运行。
- 服务器部署：未执行。
- HTTP 测试候选：`NO-GO`，等待实现和验证。
- 生产发布：`NO-GO`，HTTPS、外部签收和生产证据仍缺失。
