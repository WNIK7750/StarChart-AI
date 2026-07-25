# Agent 运行观测与模型升级门禁

## 1. 运行指标

管理员可通过 `GET /api/v1/agent/operations/metrics` 查看进程内聚合指标。接口要求 `users:manage` 权限，普通用户不可访问。

指标只包含：

- 确定性回答、Provider 成功和回退计数；
- Provider/模型标签的有界聚合；
- 最近 5 分钟请求量、Token、成本及 P50/P95 延迟；
- 完成响应重放命中数和请求标识冲突数；
- 回退率、无效输出、预算拒绝和高延迟告警。

指标不包含用户 ID、请求 ID 明细、问题、回答、Prompt、证据正文、Authorization、Cookie、API Key、IP 或 User-Agent。Provider/模型标签最多保留 16 组，额外标签合并为 `other`，最近事件最多保留 5000 项。

这些指标和并发、成本治理账本一样只存在于当前 API 进程，重启后清零。阶段 1 继续使用单 worker；多实例上线前再接入共享指标后端，不能将用户或内容标签加入时序指标。

### 1.1 每请求最小 trace

每次确定性、Provider 成功或回退结果会记录固定字段：请求标识摘要、模式、Provider、模型、尝试次数、回退原因、校验错误、提示版本、证据数量、实际只读工具、耗时、输入/输出 Token 和成本。

请求标识只记录 SHA-256 的前 24 位，不记录客户端原值；工具名来自固定允许集。`validationError` 只区分输入秘密阻断和 Provider 输出校验失败。trace 不包含用户 ID、问题、回答、Prompt、证据正文、Authorization、Cookie、API Key、IP 或 User-Agent。

默认告警：

| 告警 | 条件 |
| --- | --- |
| `AGENT_PROVIDER_FALLBACK_RATE_HIGH` | 最近 5 分钟至少 10 次请求且回退率不低于 20% |
| `AGENT_PROVIDER_INVALID_OUTPUT` | 最近 5 分钟出现至少 1 次输出守卫失败 |
| `AGENT_BUDGET_REJECTIONS_HIGH` | 最近 5 分钟出现至少 3 次预算拒绝 |
| `AGENT_LATENCY_P95_HIGH` | 最近 5 分钟至少 5 次请求且 P95 不低于 5000ms |

## 2. qwen3.7-plus 升级门禁

模型比较输入使用 `agent-model-comparison-v1`，空白结构见 `agent-model-comparison-template.json`。每条记录只保存用例 ID、试验序号、模型名、任务评分、安全/引用结果、延迟和成本，不保存 Prompt 或回答正文。文档和运行记录使用严格字段白名单，任何额外字段都会使判定失败。

输出分为两个文件：

- 稳定决策报告：只包含格式版本、输入的语义 SHA-256 和判定结果。相同 JSON 内容即使缩进或字段顺序不同，报告也完全一致，适合 CI 和跨提交比较。
- 可选归档元数据：包含输入原始字节 SHA-256、稳定报告 SHA-256 和 UTC 生成时间，只描述这次运行，不参与决策基线比较。

运行：

```powershell
$env:PYTHONPATH="backend"
python scripts/evaluate-agent-model-upgrade.py `
  --input docs/04-operations/agent/agent-model-comparison-template.json `
  --output docs/04-operations/agent/agent-model-comparison-report.json `
  --metadata-output docs/04-operations/agent/agent-model-comparison-report.metadata.json
```

只有同时满足以下条件，结果才会是 `ELIGIBLE_FOR_5_PERCENT_REVIEW`：

1. 至少 20 组相同用例、相同试验序号的配对结果；
2. `qwen3.7-plus` 没有安全或引用失败；
3. 平均任务评分相对 `qwen3.5-flash` 至少提升 0.05；
4. 平均成本不超过基线的 1.5 倍；
5. P95 延迟不超过基线的 1.5 倍。

任一条件不满足都输出 `KEEP_FLASH_0_PERCENT`。即使全部满足，也只表示可以提交人工审查，不会修改配置或自动放量。人工批准后最多先开放 5%；只有 5% 真实运行的质量、成本、回退率和延迟继续达标，才单独审查 10%。

当前没有真实模型配对数据，因此正式结论仍是：`qwen3.5-flash` 为唯一默认模型，`qwen3.7-plus` 升级比例保持 0%。

空白模板的稳定基线保存在 `docs/06-evidence/agent/agent_model_comparison_empty_report.json`。Agent 门禁会以 `--check` 核对它；当前固定结果为 `KEEP_FLASH_0_PERCENT`，原因为配对样本不足且没有可证明的质量提升。该基线只验证门禁默认关闭，不代替未来真实评测。

未来受控对比必须先按 `agent-blind-evaluation-runbook.md` 完成匿名样本分配和盲评。评分文件与模型/成本映射分离，再由 `compile-agent-blind-evaluation.py` 编译为本节的比较输入；不得手工把评分直接拼接到模型报告中。

## 3. 阶段 1 评估清单

`tests/fixtures/agent_phase1_cases.json` 的可审计摘要保存在 `docs/06-evidence/agent/agent_phase1_evaluation_manifest.json`。清单不复制用例 ID、问题或回答，只记录：

- 套件和清单格式版本；
- JSON 规范化后的语义 SHA-256；
- 20 条路由/能力用例和 10 条 Provider 输出守卫用例；
- 5 类路由意图的数量；
- 4 条允许输出、6 条拒绝输出及 6 类拒绝原因；
- CI 使用的稳定失败分类。

Agent 门禁会执行：

```powershell
python scripts/build-agent-evaluation-manifest.py --check
```

用例内容、期望、分类或数量发生变化但清单未同步时，检查返回 `EVAL_ARTIFACT_STALE`。若确需调整评估集，应先审查变更原因，再显式重新生成并同时提交测试集与清单；不能通过删除安全类别或降低数量绕过门禁。

GitHub Actions 在 Agent 门禁通过后上传阶段 1 评估清单、盲评协议清单和空白模型决策基线，保留 14 天。构建制品只用于比较套件版本、协议、语义哈希、分类统计和默认升级决策，不包含测试问题、答案、用户数据或 Provider 原始响应。
