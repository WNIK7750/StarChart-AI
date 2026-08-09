# Git 工作流与提交规划

> 状态：当前有效
> 更新日期：2026-08-09
> 用途：定义当前工作区的分支、提交、验证和发布边界；取代历史 Git 暂存清单。

## 1. 本轮集成基线

- 仓库根目录：`ai-nav-fullstack/`
- 主线：`master`（本轮开始时为 `8d16551`）
- 集成分支：`codex/agent-reliability-byok-production`
- 起始提交：`57a7d4e`（在主线之上包含学习内容稳定 ID 回填）
- 集成范围：Agent、用户模型配置、检索、前端、HTTPS 部署和目录治理

本轮改动在上述集成分支完成验证和分领域提交，再以快进方式并入 `master`。不要在未确认
工作区内容前 reset、clean、stash、rebase 或覆盖现有文件。

## 2. 提交原则

1. 一个提交只表达一个可审查的领域变化，代码、迁移、前端消费者和对应测试放在同一提交。
2. 不按文件类型机械拆分；不能把实现与测试、迁移与读取代码、API 与前端适配器分开。
3. 每个领域提交先跑该领域测试，最终候选再跑全量门禁。
4. 文档只描述已实现并已验证的事实；历史快照不能覆盖当前代码和测试。
5. `.env`、用户 API Key、SQLite 运行库、上传、日志、缓存、测试输出和发布压缩包永不提交。
6. 本地提交、推送、合并和生产发布是四个独立门禁；任何一步成功都不自动授权下一步。

## 3. 当前改动的建议提交序列

### 提交 1：仓库与 HTTPS 发布边界

建议标题：`chore: establish repository and https deployment boundaries`

范围：

- `.gitignore`、CI 路径、发布 allowlist 与启动脚本；
- `deploy/production/`、生产验证脚本和部署运维文档；
- 仓库目录规则、文档地图和带日期的历史分析快照；
- 根目录旧生产模板的删除与唯一模板迁移。

验证：

```powershell
.\scripts\verify-repository-layout.ps1
.\scripts\verify-production-deployment.ps1
```

### 提交 2：用户自带模型与凭据边界

建议标题：`feat: add user-managed agent model settings`

范围：

- `backend/app/users/model_settings/` 与 Users API；
- 迁移 `023`—`025`；
- 设置页的提供商名称、API 地址、显示名称、模型 ID、API Key 和可选最大输出；
- Windows DPAPI 本地凭据存储、服务器失败关闭规则及对应测试；
- 不提供默认模型、共享 Key 或网站成本预算。

验证：

```powershell
.\scripts\verify-users.ps1
```

### 提交 3：站内检索与证据域

建议标题：`feat: broaden site evidence retrieval`

范围：

- Learning 与 Tools 查询服务、领域 Schema 和薄 Agent 工具；
- 对原始问题的站内召回、稳定站内链接与去重排序；
- Learning、Tools 领域测试。

验证：

```powershell
.\scripts\verify-learning.ps1
.\scripts\verify-tools.ps1
```

### 提交 4：Agent 循环、反思与恢复

建议标题：`feat: add recoverable evidence-grounded agent loop`

范围：

- Base + Domain 上下文、动态工具选择、对话内上下文与诊断状态；
- 联网搜索、结构化输出、批判/重编、三次工具失败后的模型接管；
- 安全降级、SSE、运行时投影以及删除生产假 Provider；
- Fake 仅保留在 `tests/support/`，连同 Agent 专项测试提交。

验证：

```powershell
.\scripts\verify-agent.ps1
```

### 提交 5：助手与登录体验

建议标题：`feat: improve authenticated assistant experience`

范围：

- 助手页登录前置、模型配置入口、过程状态与非技术错误恢复；
- 认证会话状态、快捷助手入口、学习页接入及相关前端测试；
- 不向普通用户暴露内部实现词、原始异常、诊断编号或模型隐藏推理。

验证：

```powershell
.\scripts\verify-frontend.ps1
```

### 提交 6：当前说明与许可

建议标题：`docs: document current project and noncommercial license`

范围：

- `README.md`、`LICENSE`、当前 Agent 设计/优化流程及交接文档同步；
- README 不写死易失真的测试总数、工具总数或旧模型名称；
- 项目对外表述为“源码公开、仅限非商业使用”，不误称为 OSI 开源许可。

验证：

```powershell
git diff --check
.\scripts\verify-repository-layout.ps1
```

## 4. 最终门禁

所有提交组装完成后，从仓库根目录执行：

```powershell
.\scripts\verify-quality.ps1
.\scripts\verify-foundation.ps1
.\scripts\verify-agent.ps1
.\scripts\verify-production-deployment.ps1
git diff --check
```

只有全部通过，才能把分支标记为“可提交评审”。推送、创建 PR、部署 HTTPS 和真实用户模型
验收仍需分别执行；不得用本地假实现、固定响应或旧证据代替真实链路验收。

## 5. 暂存检查

每个提交只暂存该节列出的路径，然后检查：

```powershell
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
```

发现 `.env`、凭据、数据库、日志、上传、缓存或发布包时立即停止。若某个提交不能在不破坏
依赖的情况下独立通过领域测试，应与其直接依赖的相邻提交合并，并在提交正文中说明原因；
不要为了追求提交数量制造不可运行的中间状态。
