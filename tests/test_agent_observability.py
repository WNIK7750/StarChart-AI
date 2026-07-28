import json
import inspect
import unittest
from unittest.mock import patch

import httpx
from app.agent.model_gate import (
    ModelComparisonInvalid,
    evaluate_model_upgrade,
)
from app.agent.observability import (
    TRACE_FIELDS,
    AgentMetrics,
    build_agent_trace,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentChatRequest
from app.core.config import validate_agent_runtime_topology


def comparison_document(
    *,
    count: int = 20,
    baseline_score: float = 0.8,
    candidate_score: float = 0.87,
    baseline_cost: float = 0.001,
    candidate_cost: float = 0.0014,
    baseline_latency: float = 1000,
    candidate_latency: float = 1300,
    candidate_safety: bool = True,
    candidate_grounding: bool = True,
) -> dict:
    runs = []
    for index in range(count):
        runs.extend(
            (
                {
                    "caseId": f"case-{index}",
                    "trial": 1,
                    "model": "qwen3.5-flash",
                    "taskScore": baseline_score,
                    "safetyPassed": True,
                    "groundingPassed": True,
                    "latencyMs": baseline_latency,
                    "costCny": baseline_cost,
                },
                {
                    "caseId": f"case-{index}",
                    "trial": 1,
                    "model": "qwen3.7-plus",
                    "taskScore": candidate_score,
                    "safetyPassed": candidate_safety,
                    "groundingPassed": candidate_grounding,
                    "latencyMs": candidate_latency,
                    "costCny": candidate_cost,
                },
            )
        )
    return {
        "version": "agent-model-comparison-v1",
        "baselineModel": "qwen3.5-flash",
        "candidateModel": "qwen3.7-plus",
        "runs": runs,
    }


class AgentMetricsTests(unittest.IsolatedAsyncioTestCase):
    def test_request_trace_is_bounded_content_free_and_complete(self):
        trace = build_agent_trace(
            request_id="sk-secret-shaped-request-id",
            mode="deterministic",
            provider="openai_compatible",
            model="qwen3.5-flash",
            attempts=9,
            fallback_reason="invalid_output",
            prompt_version="agent-readonly-v1",
            evidence_count=999,
            tools=(
                "tools.search",
                "learning.search",
                "tools.search",
                "unapproved.tool",
            ),
            latency_ms=12.345,
            input_tokens=100,
            output_tokens=20,
            cost_cny=0.00123456789,
        )
        rendered = json.dumps(trace, ensure_ascii=False)

        self.assertEqual(TRACE_FIELDS, set(trace))
        self.assertEqual(24, len(trace["requestId"]))
        self.assertNotIn("sk-secret-shaped-request-id", rendered)
        self.assertEqual(2, trace["attempts"])
        self.assertEqual(100, trace["evidenceCount"])
        self.assertEqual(
            ["learning.search", "tools.search"],
            trace["tools"],
        )
        self.assertEqual("invalid_output", trace["validationError"])
        for forbidden in ('"message":', '"answer":', '"userId":', '"prompt":'):
            self.assertNotIn(forbidden, rendered)

    def test_process_local_agent_state_requires_one_declared_worker(self):
        validate_agent_runtime_topology(1, "process_local")
        with self.assertRaisesRegex(RuntimeError, "AI_NAV_API_WORKERS=1"):
            validate_agent_runtime_topology(2, "process_local")
        with self.assertRaisesRegex(RuntimeError, "not implemented"):
            validate_agent_runtime_topology(1, "redis")

    def test_metrics_aggregate_without_user_or_content_labels(self):
        now = [1000.0]
        metrics = AgentMetrics(clock=lambda: now[0])
        metrics.record(
            mode="provider",
            provider="openai_compatible",
            model="qwen3.5-flash",
            fallback_reason=None,
            latency_ms=120,
            input_tokens=100,
            output_tokens=20,
            cost_cny=0.001,
        )
        metrics.record_replay_hit()
        metrics.record_request_id_conflict()

        snapshot = metrics.snapshot()

        self.assertEqual(1, snapshot["recent"]["requestCount"])
        self.assertEqual(0.001, snapshot["recent"]["costCny"])
        self.assertEqual(1, snapshot["counters"]["replayHits"])
        self.assertEqual(1, snapshot["counters"]["requestIdConflicts"])
        self.assertFalse(snapshot["meta"]["containsPii"])
        self.assertFalse(snapshot["meta"]["containsContent"])
        rendered = json.dumps(snapshot, ensure_ascii=False)
        for forbidden in ('"requestId":', '"userId":', '"message":', '"answer":'):
            self.assertNotIn(forbidden, rendered)

    def test_metrics_window_alerts_and_bounded_model_cardinality(self):
        now = [1000.0]
        metrics = AgentMetrics(clock=lambda: now[0])
        for index in range(20):
            metrics.record(
                mode="deterministic",
                provider=f"provider-{index}",
                model=f"model-{index}",
                fallback_reason="invalid_output" if index < 4 else None,
                latency_ms=6000,
                input_tokens=0,
                output_tokens=0,
                cost_cny=None,
            )

        snapshot = metrics.snapshot()
        codes = {alert["code"] for alert in snapshot["alerts"]}
        self.assertIn("AGENT_PROVIDER_FALLBACK_RATE_HIGH", codes)
        self.assertIn("AGENT_PROVIDER_INVALID_OUTPUT", codes)
        self.assertIn("AGENT_LATENCY_P95_HIGH", codes)
        self.assertLessEqual(
            len(snapshot["counters"]["models"]),
            AgentMetrics.MAX_MODEL_LABELS + 1,
        )

        now[0] += AgentMetrics.WINDOW_SECONDS + 1
        self.assertEqual(0, metrics.snapshot()["recent"]["requestCount"])

    async def test_pure_deterministic_requests_are_observed(self):
        metrics = AgentMetrics()
        orchestrator = AgentOrchestrator()
        with (
            patch(
                "app.agent.orchestrator.get_agent_metrics",
                return_value=metrics,
            ),
            patch("app.agent.orchestrator.agent_logger.info") as log_info,
        ):
            await orchestrator.respond(
                AgentChatRequest(message="介绍 RAG"),
                request_id="observed-request",
            )

        snapshot = metrics.snapshot()
        self.assertEqual(1, snapshot["recent"]["requestCount"])
        self.assertEqual(
            "deterministic",
            snapshot["counters"]["outcomes"][0]["outcome"],
        )
        trace = json.loads(log_info.call_args.args[0])
        self.assertTrue(trace["tools"])
        self.assertEqual("agent-readonly-v1", trace["promptVersion"])
        self.assertIsNone(trace["validationError"])
        self.assertEqual(TRACE_FIELDS, set(trace))

    async def test_metrics_http_contract_requires_users_manage(self):
        from app.main import app, iter_app_routes

        route = next(
            route
            for route in iter_app_routes()
            if getattr(route, "path", None) == "/api/v1/agent/operations/metrics"
        )
        auth_dependency = route.dependant.dependencies[0].call
        self.assertEqual(
            "users:manage",
            inspect.getclosurevars(auth_dependency).nonlocals["permission"],
        )
        previous_overrides = dict(app.dependency_overrides)
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                unauthorized = await client.get("/api/v1/agent/operations/metrics")
                self.assertEqual(401, unauthorized.status_code)

                app.dependency_overrides[auth_dependency] = lambda: {
                    "id": 1,
                    "permissions": ["users:manage"],
                }
                authorized = await client.get("/api/v1/agent/operations/metrics")
                self.assertEqual(200, authorized.status_code)
                self.assertFalse(authorized.json()["meta"]["containsPii"])
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)


class AgentModelUpgradeGateTests(unittest.TestCase):
    def test_material_safe_cost_effective_gain_is_reviewable_not_automatic(self):
        report = evaluate_model_upgrade(comparison_document())

        self.assertEqual("ELIGIBLE_FOR_5_PERCENT_REVIEW", report["decision"])
        self.assertFalse(report["automaticRoutingChange"])
        self.assertTrue(report["meta"]["requiresHumanApproval"])
        self.assertEqual([], report["reasons"])

    def test_missing_evidence_keeps_flash_at_zero_percent(self):
        report = evaluate_model_upgrade(comparison_document(count=5))

        self.assertEqual("KEEP_FLASH_0_PERCENT", report["decision"])
        self.assertIn("INSUFFICIENT_PAIRED_CASES", report["reasons"])

    def test_safety_grounding_cost_latency_or_quality_failure_blocks_upgrade(self):
        cases = (
            (
                comparison_document(candidate_safety=False),
                "CANDIDATE_SAFETY_FAILURE",
            ),
            (
                comparison_document(candidate_grounding=False),
                "CANDIDATE_GROUNDING_FAILURE",
            ),
            (
                comparison_document(candidate_score=0.82),
                "QUALITY_GAIN_NOT_MATERIAL",
            ),
            (
                comparison_document(candidate_cost=0.002),
                "COST_RATIO_TOO_HIGH",
            ),
            (
                comparison_document(candidate_latency=2000),
                "LATENCY_RATIO_TOO_HIGH",
            ),
        )
        for document, expected_reason in cases:
            with self.subTest(reason=expected_reason):
                report = evaluate_model_upgrade(document)
                self.assertEqual("KEEP_FLASH_0_PERCENT", report["decision"])
                self.assertIn(expected_reason, report["reasons"])

    def test_gate_rejects_unapproved_models_and_duplicate_runs(self):
        wrong_model = comparison_document()
        wrong_model["candidateModel"] = "unapproved-model"
        with self.assertRaises(ModelComparisonInvalid):
            evaluate_model_upgrade(wrong_model)

        duplicate = comparison_document()
        duplicate["runs"].append(dict(duplicate["runs"][0]))
        with self.assertRaises(ModelComparisonInvalid):
            evaluate_model_upgrade(duplicate)

        content_bearing = comparison_document()
        content_bearing["runs"][0]["prompt"] = "不得进入评测归档"
        with self.assertRaises(ModelComparisonInvalid):
            evaluate_model_upgrade(content_bearing)

    def test_report_contains_scores_not_prompts_or_responses(self):
        report = evaluate_model_upgrade(comparison_document())
        rendered = str(report)

        self.assertNotIn("userMessage", rendered)
        self.assertNotIn("'answer':", rendered)
        self.assertNotIn("case-0", rendered)


if __name__ == "__main__":
    unittest.main()
