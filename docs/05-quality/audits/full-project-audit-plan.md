# AI 知识导航全项目审计计划

> 版本：1.0  
> 审计基准：2026-07-25  
> 审计对象：`ai-nav-fullstack` 当前工作树  
> 审计结论入口：`docs/05-quality/audits/full-project-audit-report.md`

## 1. 目标与边界

本次审计回答四个问题：

1. 当前代码是否符合既定的模块化单体边界；
2. 自动化测试通过是否足以支撑安全、数据与发布结论；
3. 哪些问题会阻止生产上线，哪些属于后续工程治理；
4. 文档、机器证据、脚本和 CI 引用是否形成可重复的审计闭环。

审计覆盖后端、前端、数据库、迁移、Agent、认证与隐私、依赖供应链、测试、CI、运维和全部文档。真实 `.env`、真实 Provider Key、真实用户数据和生产基础设施不在本次读取或调用范围内。

## 2. 采用的权威框架

| 框架 | 本项目用途 | 裁剪方式 |
| --- | --- | --- |
| [NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) | 开发流程、依赖、变更、漏洞与发布证据 | 只保留适用于单仓库、小团队的可验证任务 |
| [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/) | Web、API、认证、会话、访问控制、文件与配置 | 以 Level 2 为目标，按适用性记录通过、失败或不适用 |
| [OWASP AISVS](https://owasp.org/www-project-artificial-intelligence-security-verification-standard-aisvs-docs/) | Provider、模型输入输出、数据边界、成本与关闭开关 | 仅审计当前 Agent/Provider 边界，不扩展到模型训练治理 |
| [Google SRE Production Readiness Review](https://sre.google/sre-book/evolving-sre-engagement-model/) | 可观测性、容量、变更、应急、回滚和依赖 | 作为上线门禁，不把本地基准冒充生产 SLO |
| [GitHub Actions 安全使用](https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats) | CI 最小权限、Action 固定、供应链风险 | 审计当前唯一工作流及依赖更新机制 |

## 3. 风险分级

| 级别 | 定义 | 处理时限 |
| --- | --- | --- |
| P0 严重 | 已确认可直接导致大范围数据泄露、不可逆破坏或远程接管 | 立即停止发布并修复 |
| P1 高 | 可导致账户接管、已知漏洞暴露、生产数据风险或关键门禁失效 | 上线前必须修复 |
| P2 中 | 防御纵深、契约、供应链或质量控制存在明显缺口 | 上线前评审并排期，能低成本修复则纳入门禁 |
| P3 低 | 可维护性、文档、风格或局部工程债 | 常规迭代处理 |

所有发现必须包含代码或运行证据、影响、修复建议和复验条件。未验证的推测不得写成已确认缺陷。

## 4. 审计工作包

| 工作包 | 任务 | 主要证据 | 状态 |
| --- | --- | --- | --- |
| AUD-01 基线冻结 | 保存分支、提交、脏工作树与文件清单 | `git status --short --branch`、文件清单 | 完成 |
| AUD-02 架构 | 检查 Router/Service/Repository、跨域依赖和 Agent 所有权 | import/SQL 静态检索、模块代码 | 完成 |
| AUD-03 API | 核对路由数量、认证依赖、请求/响应 DTO、错误语义 | FastAPI 路由运行时清单、OpenAPI 基线 | 完成 |
| AUD-04 数据 | 复验 20 个迁移、checksum、外键、完整性、备份与恢复 | Foundation 门禁、恢复演练 JSON | 完成 |
| AUD-05 安全 | 认证、恢复、会话、RBAC、隐私、上传、SSRF、密钥与配置 | 代码审查、安全基线、ASVS/NIST 对照 | 完成 |
| AUD-06 Agent | Provider 关闭开关、证据边界、输出守卫、成本、并发与会话 | Agent 门禁、评估清单、运行态测试 | 完成 |
| AUD-07 前端 | XSS 面、令牌存储、链接安全、响应式和可访问性 | Node 测试、静态检索、既有浏览器证据 | 完成 |
| AUD-08 供应链 | 依赖漏洞、版本固定、CI Action 与最小权限 | `pip-audit`、requirements、工作流 | 完成 |
| AUD-09 质量 | 全量门禁、静态检查、覆盖率与复杂度治理 | Foundation/Agent 门禁、Ruff 检查 | 完成 |
| AUD-10 生产就绪 | 配置、健康检查、日志、容量、回滚和外部依赖 | 配置契约、运行时响应头探测、Runbook | 完成 |
| AUD-11 文档 | 分类、权威层级、陈旧声明、路径与生成器一致性 | 文档索引、路径检查、门禁复跑 | 完成 |

## 5. 执行顺序

```text
基线冻结
  -> 离线门禁复跑
  -> 架构/API/数据审计
  -> 安全/Agent/前端审计
  -> 依赖与 CI 审计
  -> 生产就绪评审
  -> 风险分级与整改任务
  -> 文档重组、引用修复和最终复验
```

## 6. 证据与复验规则

- 当前代码与自动化测试优先于历史规划文档。
- 本地性能数字只作为回归基线，不代表生产 SLA。
- `pip-audit` 发现按包、版本、公告 ID 和最低修复版本记录。
- 安全问题采用“攻击前提—影响—现有缓解—剩余风险”表述。
- 外部合规、真实 Provider、上海到北京网络和生产容量无法在本地闭环，必须明确标为外部待签收。
- 修复 P1 后必须重新运行 Foundation、Agent、依赖审计和针对性安全测试。

## 7. 上线退出条件

生产状态只有在以下条件全部满足后才能从 `NO-GO` 改为 `GO`：

1. 所有 P1 已关闭并留存复验证据；
2. Foundation 和 Agent 门禁通过；
3. 依赖审计没有适用的已知高风险漏洞；
4. 生产配置样例/部署清单覆盖密钥、数据库、Cookie、CORS、代理和危险开关；
5. Provider 合规、真实调用、容量、备份、回滚和监控完成人工签收；
6. 审计报告的风险接受项有责任人、期限和书面理由。
