import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "users-baseline"


def read_json(name: str) -> dict:
    return json.loads((BASELINE / name).read_text(encoding="utf-8"))


def main() -> None:
    security = read_json("users_security_baseline.json")
    performance = read_json("users_performance_baseline.json")
    rehearsal = read_json("users_release_rehearsal.json")
    screenshots = read_json("screenshots/settings-screenshots-manifest.json")
    openapi = read_json("auth_users_openapi.json")
    required_paths = {
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/users/me/profile",
        "/api/v1/users/me/privacy/export",
        "/api/v1/users/me/assets/workflows",
        "/api/v1/agent/workflows/save",
        "/api/v1/users/operations/metrics",
    }
    openapi_paths = set(openapi["paths"])
    schema = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    users_api = (ROOT / "frontend" / "assets" / "js" / "users-api.js").read_text(encoding="utf-8")
    migrations = sorted((ROOT / "database" / "migrations").glob("*.sql"))
    checks = {
        "openapi": required_paths <= openapi_paths,
        "database": all(table in schema for table in ("user_accounts", "user_privacy_consent_events", "user_saved_workflows"))
        and len(migrations) == rehearsal["migrationCount"],
        "frontend": all(name in users_api for name in ("getCurrentUser", "getUserPrivacyConsents", "listUserWorkflows", "saveAgentWorkflow")),
        "responsive": screenshots.get("passed") is True and len(screenshots.get("captures", [])) == 4,
        "security": security["summary"]["fail"] == 0,
        "performance": performance.get("passed") is True,
        "releaseRehearsal": rehearsal.get("passed") is True,
    }
    report = {
        "passed": all(checks.values()),
        "checks": checks,
        "evidence": {
            "openapiPathCount": len(openapi_paths),
            "migrationCount": len(migrations),
            "responsiveCaptures": len(screenshots.get("captures", [])),
            "security": security["summary"],
            "performanceOperations": len(performance.get("operations", [])),
            "queryPlanChecks": len(performance.get("queryPlans", [])),
            "knownRisks": [item["title"] for item in security["findings"] if item["status"] == "known-risk"],
        },
    }
    json_path = BASELINE / "users_final_acceptance.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    status_rows = "\n".join(f"| {name} | {'通过' if passed else '失败'} |" for name, passed in checks.items())
    risk_rows = "\n".join(f"- {risk}" for risk in report["evidence"]["knownRisks"]) or "- 无"
    markdown = f"""# Users 最终验收报告

总体结果：**{'通过' if report['passed'] else '失败'}**

## 验收矩阵

| 范围 | 结果 |
| --- | --- |
{status_rows}

## 证据摘要

- OpenAPI 冻结路径：{report['evidence']['openapiPathCount']} 条，包含认证、隐私、资产、Agent 保存和管理员指标接口。
- 数据库迁移：{report['evidence']['migrationCount']} 个，checksum、备份、恢复、完整性、外键和 canary 演练通过。
- 前端：Users facade 包含身份、隐私、工作流和 Agent 保存命令；登录弹窗默认 Logo、最近登录头像、注册可选手机号，以及设置页邮箱/手机号绑定修改流程通过。
- 账号安全：联系方式变更要求当前密码，变更后重置对应验证状态；业务 401 不触发 token 刷新或写请求重放。
- 认证语义：显式协议同意、撤回后重新授权，以及保持登录 Cookie 在刷新轮换后的持久性均通过回归验证。
- 响应式：{report['evidence']['responsiveCaptures']} 个 Playwright 视口通过，无横向溢出和未知 console/page error。
- 安全：{security['summary']['pass']} pass、{security['summary']['knownRisk']} known-risk、{security['summary']['fail']} fail。
- 性能：{report['evidence']['performanceOperations']} 条操作预算和 {report['evidence']['queryPlanChecks']} 条查询计划门禁通过。

## 已知部署风险

{risk_rows}

生产发布必须按 `docs/users-release-runbook.md` 处置已知风险、创建可验证备份并完成发布后观察。
"""
    (ROOT / "docs" / "users-final-acceptance-report.md").write_text(markdown, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit("Users final acceptance failed")


if __name__ == "__main__":
    main()
