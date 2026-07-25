# AI 知识导航文档地图

> 版本：2026-07-25  
> 目标：让设计、实现、运维、审计和机器证据各有唯一入口。

## 1. 权威阅读顺序

1. 当前独立复验与发布判断：`docs/05-quality/audits/full-project-remediation-verification-report.md`
2. Git 提交执行交接：`docs/05-quality/audits/git-commit-readiness-handoff.md`
3. 当前整改实施记录：`docs/05-quality/audits/full-project-remediation-report.md`
4. 审计整改文件路由：`docs/00-index/remediation-file-index.md`
5. 上一轮问题回测：`docs/05-quality/audits/full-project-reaudit-report.md`
6. 首轮完整审计：`docs/05-quality/audits/full-project-audit-report.md`
7. 当前成果交接：`docs/01-overview/fullstack-development-results-handoff.md`
8. 全局架构边界：`docs/02-architecture/modular-monolith-guidelines.md`
9. 领域现状：`docs/03-domains/<domain>/`
10. 发布与运维：`docs/04-operations/<domain>/`
11. 机器证据：`docs/06-evidence/<domain>/`
12. 历史规划与任务文档只解释演进过程，不覆盖当前代码与审计结论。

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
| `00-index/` | 文档地图、治理规则 | 所有人 |
| `01-overview/` | 全项目交接、总路线 | 负责人、审计人 |
| `02-architecture/` | 模块化单体、数据库、ADR | 架构与后端 |
| `03-domains/` | Frontend、Learning、Tools、Users、Agent 领域文档 | 领域开发者 |
| `04-operations/` | Content、Users、Agent 运维与发布手册 | 发布与运维 |
| `05-quality/` | 审计计划、审计报告和质量基线说明 | QA、安全、负责人 |
| `06-evidence/` | JSON、截图、基准和脱敏演练产物 | 自动化与审计 |
| `07-prompts/` | 历史执行提示词 | 仅供追溯 |

## 3. 领域入口

### Frontend

- `docs/03-domains/frontend/frontend-audit.md`

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

- `docs/03-domains/agent/agent-development-handoff.md`
- `docs/03-domains/agent/agent-development-tasks.md`
- `docs/02-architecture/decisions/`
- `docs/04-operations/agent/`
- `docs/06-evidence/agent/`

### 审计整改提示词

- `docs/07-prompts/audits/full-project-remediation-prompt.md`
- `docs/07-prompts/audits/full-project-remediation-verification-prompt.md`
- `docs/05-quality/audits/full-project-remediation-verification-report.md`
- `docs/05-quality/audits/full-project-remediation-report.md`
- `docs/05-quality/audits/git-commit-readiness-handoff.md`
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

- 原根目录 Markdown 已全部归入对应分类；
- 原 `decisions/` 已归入 `02-architecture/decisions/`；
- 原 `operations/` 已按 Agent 运维归入 `04-operations/agent/`；
- 原 Agent/Users baseline 已归入 `06-evidence/agent/` 与 `06-evidence/users/`；
- 原提示词已归入 `07-prompts/users/`；
- 脚本、测试、CI、README、JSON 内路径和 Markdown 引用已同步迁移。

后续新增文档时，应优先扩展现有目录，不再创建含义重叠的“最终版”“最新版”或“完成版”文件。
