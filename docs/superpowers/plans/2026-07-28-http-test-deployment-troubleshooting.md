# HTTP Test Deployment Troubleshooting Documentation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将本次 HTTP 测试部署遇到的真实故障整理成可检索、无秘密、可复验的故障排查手册。

**Architecture:** 新增一份独立运维文档作为唯一故障入口，不继续扩张主运行手册。运行手册、HTTP 部署索引、文档地图和 README 只保留简短链接，避免同一解决方案出现多个版本。

**Tech Stack:** Markdown、现有秘密扫描器、文档路径检查与 Git 差异检查。

## Global Constraints

- 不记录公网 IP、测试账号标识、密码、Token、Cookie、真实 `.env` 或 Provider 请求/响应。
- 只记录本次实际出现或实际验证过的故障；未执行的恢复、回滚、HTTPS 和 Provider 验证保持 `NOT RUN`。
- 每个故障条目必须包含现象、根因、推荐处理、验证方法和误判边界。
- 不运行与文档修改无关的全项目长测试套件。

---

### Task 1: 编写独立故障排查手册

**Files:**
- Create: `docs/04-operations/deployment/http-test-deployment-troubleshooting.md`

**Interfaces:**
- Consumes: `docs/04-operations/deployment/http-test-deployment-runbook.md` 和 `docs/06-evidence/platform/http-test-server-validation.json`
- Produces: 后续部署人员的故障检索入口

- [x] **Step 1: 按部署阶段建立快速定位表**

覆盖 SSH、发布包、Python、systemd、Nginx、SQLite、Agent、Windows/SCP、证据和验证耗时。

- [x] **Step 2: 为每项写入可验证的推荐处理**

所有命令使用占位变量或固定非秘密路径；明确哪些输出不能复制到聊天或 Git。

- [x] **Step 3: 自查未执行事项**

确认没有把备份完整性写成恢复通过，没有把 HTTP 测试写成生产发布。

### Task 2: 接入文档导航并验证

**Files:**
- Modify: `docs/04-operations/deployment/http-test-deployment-runbook.md`
- Modify: `docs/00-index/http-test-deployment-file-index.md`
- Modify: `docs/00-index/documentation-map.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1 的稳定路径
- Produces: 从 README、地图、索引和运行手册可达的统一入口

- [x] **Step 1: 增加最小交叉链接**

不在四个入口复制故障正文。

- [x] **Step 2: 运行文档专项验证**

```powershell
python scripts/check-no-secrets.py --paths `
  docs/04-operations/deployment/http-test-deployment-troubleshooting.md `
  docs/04-operations/deployment/http-test-deployment-runbook.md `
  docs/00-index/http-test-deployment-file-index.md `
  docs/00-index/documentation-map.md `
  README.md
git diff --check
```

Expected: 秘密扫描 0 命中，Git 差异检查退出码 0。

- [ ] **Step 3: 提交**

```powershell
git add docs/04-operations/deployment/http-test-deployment-troubleshooting.md `
  docs/04-operations/deployment/http-test-deployment-runbook.md `
  docs/00-index/http-test-deployment-file-index.md `
  docs/00-index/documentation-map.md `
  README.md `
  docs/superpowers/plans/2026-07-28-http-test-deployment-troubleshooting.md
git commit -m "docs: add HTTP deployment troubleshooting guide"
```
