# AI 知识导航文档地图

> 版本：2026-08-09
> 目标：让设计、实现、运维、审计和机器证据各有唯一入口。

## 1. 权威阅读顺序

1. 仓库唯一入口与 HTTPS 文件边界：`docs/00-index/repository-layout.md`
2. 当前 Git 工作流与提交规划：`docs/00-index/git-workflow.md`
3. 当前 Agent 推荐工作流设计：`docs/03-domains/agent/agent-content-recommendation-workflow-design.md`
4. 当前 Agent 优化与验证流程：`docs/03-domains/agent/agent-content-recommendation-optimization-flow.md`
5. HTTPS 生产部署：`docs/04-operations/deployment/https-production-deployment-runbook.md`
6. 全局架构边界：`docs/02-architecture/modular-monolith-guidelines.md`
7. 领域现状：`docs/03-domains/<domain>/`
8. 发布与运维：`docs/04-operations/<domain>/`
9. 当前质量检查与机器证据：`docs/05-quality/`、`docs/06-evidence/`
10. 2026-07 审计、交接、HTTP 测试部署和历史规划只解释演进过程，不覆盖当前代码、迁移和测试。

发生冲突时，采用以下优先级：

```text
当前代码/迁移/自动化测试
  > 当前审计报告
  > 机器证据
  > 成果交接
  > 领域设计与运维手册
  > 历史路线图、任务书和提示词
```

## 2. 目录职责

| 目录 | 内容 | 主要读者 |
| --- | --- | --- |
| `00-index/` | 文档地图、仓库规则与 Git 工作流 | 所有人 |
| `01-overview/` | 全项目交接、总路线 | 负责人、审计人 |
| `02-architecture/` | 模块化单体、数据库、ADR | 架构与后端 |
| `03-domains/` | Frontend、Learning、Tools、Users、Agent 领域文档 | 领域开发者 |
| `04-operations/` | Content、Users、Agent 运维与发布手册 | 发布与运维 |
| `05-quality/` | 审计计划、审计报告和质量基线说明 | QA、安全、负责人 |
| `06-evidence/` | JSON、截图、基准和脱敏演练产物 | 自动化与审计 |
| `07-prompts/` | 历史执行提示词 | 仅供追溯 |

仓库源码与本地生成物的完整边界见 `docs/00-index/repository-layout.md`。带日期的
`05-quality/analysis/` 子目录是历史快照，必须保留日期和非当前状态说明。

## 3. 领域入口

### Frontend

- `docs/03-domains/frontend/frontend-audit.md`
- `docs/03-domains/frontend/quick-assistant-launcher-delivery.md`

### Learning

- `docs/03-domains/learning/learning-area-foundation-plan.md`
- `docs/03-domains/learning/learning-area-implementation.md`

### Tools

- `docs/03-domains/tools/tools-service-implementation.md`
- `docs/03-domains/tools/tool-page-optimization.md`

### Users

- `docs/03-domains/users/users-area-optimization-guide.md`
- `docs/03-domains/users/users-area-task-backlog.md`
- `docs/03-domains/users/users-final-acceptance-report.md`
- `docs/04-operations/users/users-release-runbook.md`
- `docs/06-evidence/users/`

### Agent

- `docs/03-domains/agent/agent-content-recommendation-workflow-design.md`
- `docs/03-domains/agent/agent-content-recommendation-optimization-flow.md`
- `docs/03-domains/agent/agent-development-handoff.md`
- `docs/03-domains/agent/agent-development-tasks.md`
- `docs/02-architecture/decisions/`
- `docs/04-operations/agent/`
- `docs/06-evidence/agent/`

### HTTPS 生产部署

- `docs/00-index/repository-layout.md`
- `docs/04-operations/deployment/https-production-deployment-runbook.md`
- `deploy/production/env.example`
- `deploy/production/nginx/`
- `deploy/production/systemd/`
- `deploy/production/scripts/`
- `scripts/verify-production-deployment.ps1`

### HTTP 测试部署

- `docs/00-index/http-test-deployment-file-index.md`
- `docs/01-overview/assistant-site-performance-local-deploy-git-handoff-20260729.md`
- `docs/01-overview/http-subpath-test-deployment-implementation-plan.md`
- `docs/02-architecture/deployment/http-subpath-test-deployment-design.md`
- `docs/04-operations/deployment/http-test-deployment-runbook.md`
- `docs/04-operations/deployment/http-test-deployment-troubleshooting.md`
- `docs/05-quality/audits/http-test-assistant-site-performance-20260729.md`
- `docs/superpowers/specs/2026-07-29-clean-http-routes-design.md`
- `docs/superpowers/plans/2026-07-29-clean-http-routes.md`
- `docs/06-evidence/platform/http-test-deployment-manifest.json`
- `docs/06-evidence/platform/http-test-server-validation.json`

任务 1–13 的上一 deterministic HTTP release 已完成并有历史 `GO` 证据。2026-07-29 当前候选又完成干净页面地址、旧 `.html` 308 兼容、本地 8088 smoke 和桌面/移动 Playwright 验收，完整仓库本地候选为 `GO`；当前提交仍未部署到 HTTP 测试服务器，不得把上一 release 的 `GO` 套用到当前 worktree。真实 Provider 预览、HTTPS、备份恢复、回滚演练、容量、合规和外部生产签收尚未执行，生产发布继续 `NO-GO`。

### 审计整改提示词

- `docs/07-prompts/audits/full-project-remediation-prompt.md`
- `docs/07-prompts/audits/full-project-remediation-verification-prompt.md`
- `docs/05-quality/audits/full-project-remediation-verification-report.md`
- `docs/05-quality/audits/full-project-remediation-report.md`
- `docs/05-quality/audits/git-commit-readiness-handoff.md`
- `docs/05-quality/audits/git-http-privacy-audit.md`
- `docs/06-evidence/platform/dependency_input_remediation.json`
- `docs/04-operations/production-external-signoff-checklist.md`

## 4. 文件治理规则

- 新文档必须进入职责目录，不在 `docs/` 根目录堆放文件。
- 每份文档首屏应说明用途、状态、日期和权威性。
- 规划文档不能用未验证的未来状态覆盖当前事实。
- 机器生成物只能由对应脚本更新，文件位置变更时同步修改脚本、测试和 CI。
- 基准 JSON 不存真实用户内容、凭据、Provider 请求/响应正文或可识别身份。
- 本地服务器日志不是权威证据，不应提交；需要留存时先脱敏并说明采集窗口。
- 路径统一写为仓库相对路径并使用 `/`。
- 文档移动后必须运行路径检查、两套门禁和 `git diff --check`。

## 5. 本次整理结果

- 唯一运行源码保持为 `backend/`、`frontend/`、`database/`，部署覆盖层统一位于 `deploy/`；
- 2026-08-02 全栈分析移入 `docs/05-quality/analysis/2026-08-02-full-stack-snapshot/` 并标记历史快照；
- 旧 `frontend - 副本/` 已移除，不再存在可被误用的第二套前端；
- 生产配置模板从根目录收敛为 `deploy/production/env.example`；
- 新增 `scripts/verify-repository-layout.ps1` 和对应测试，检查唯一入口、连续迁移、退役路径和误跟踪运行产物；
- HTTPS 覆盖层与仓库结构变更已纳入 CI 路径触发条件；
- `.repo-backups/` 作为恢复资料保留，本地日志、缓存、测试结果和历史发布 ZIP 已清理。

后续新增文档时，应优先扩展现有目录，不再创建含义重叠的“最终版”“最新版”或“完成版”文件。
