from copy import deepcopy
import json
import unittest

from app.agent.evaluation_protocol import (
    BlindEvaluationInvalid,
    build_blind_protocol_manifest,
    compile_blind_comparison,
)
from app.agent.model_gate import evaluate_model_upgrade


def protocol_documents(count: int = 20) -> tuple[dict, dict, set[str]]:
    case_ids = {f"case-{index:02d}" for index in range(count)}
    assignments = []
    scores = []
    for index, case_id in enumerate(sorted(case_ids)):
        for slot, model, task_score, latency, cost in (
            ("b", "qwen3.5-flash", 0.75, 1000, 0.001),
            ("c", "qwen3.7-plus", 1.0, 1200, 0.0012),
        ):
            sample_id = f"sample_{slot}{index:07d}"
            assignments.append(
                {
                    "sampleId": sample_id,
                    "caseId": case_id,
                    "trial": 1,
                    "model": model,
                    "latencyMs": latency,
                    "costCny": cost,
                }
            )
            scores.append(
                {
                    "sampleId": sample_id,
                    "taskScore": task_score,
                    "safetyPassed": True,
                    "groundingPassed": True,
                }
            )
    return (
        {
            "version": "agent-blind-assignment-v1",
            "suiteVersion": "agent-phase1-v1",
            "rubricVersion": "agent-model-rubric-v1",
            "assignments": assignments,
        },
        {
            "version": "agent-blind-scores-v1",
            "rubricVersion": "agent-model-rubric-v1",
            "scores": scores,
        },
        case_ids,
    )


class AgentBlindEvaluationProtocolTests(unittest.TestCase):
    def test_protocol_manifest_is_content_free_and_declares_enforced_contract(self):
        manifest = build_blind_protocol_manifest()
        rendered = json.dumps(manifest, ensure_ascii=False)

        self.assertEqual(
            "agent-blind-protocol-manifest-v1",
            manifest["schemaVersion"],
        )
        self.assertEqual(20, manifest["limits"]["minimumUniqueCases"])
        self.assertEqual(
            [0.0, 0.25, 0.5, 0.75, 1.0],
            manifest["limits"]["taskScoreValues"],
        )
        self.assertNotIn("model", manifest["documentFields"]["scoreRecord"])
        self.assertFalse(manifest["privacy"]["scoreContainsModel"])
        self.assertFalse(manifest["privacy"]["containsCaseContent"])
        self.assertNotIn("RAG是什么", rendered)
        self.assertNotIn('"answer"', rendered)

    def test_blind_scores_compile_into_an_approved_comparison(self):
        assignments, scores, case_ids = protocol_documents()
        comparison = compile_blind_comparison(
            assignments,
            scores,
            allowed_case_ids=case_ids,
        )
        decision = evaluate_model_upgrade(comparison)

        self.assertEqual(40, len(comparison["runs"]))
        self.assertEqual(
            "ELIGIBLE_FOR_5_PERCENT_REVIEW",
            decision["decision"],
        )
        self.assertFalse(decision["automaticRoutingChange"])
        score_source = json.dumps(scores, ensure_ascii=False)
        self.assertNotIn("qwen3.5-flash", score_source)
        self.assertNotIn("qwen3.7-plus", score_source)
        self.assertNotIn("latencyMs", score_source)
        self.assertNotIn("costCny", score_source)

    def test_score_document_rejects_model_or_content_fields(self):
        assignments, scores, case_ids = protocol_documents()
        for field, value in (
            ("model", "qwen3.5-flash"),
            ("prompt", "不得进入评分文件"),
            ("answer", "不得进入评分文件"),
        ):
            invalid = deepcopy(scores)
            invalid["scores"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                BlindEvaluationInvalid,
                "BLIND_EVAL_SCORE_SCHEMA_INVALID",
            ):
                compile_blind_comparison(
                    assignments,
                    invalid,
                    allowed_case_ids=case_ids,
                )

    def test_sample_sets_and_model_pairs_must_be_complete(self):
        assignments, scores, case_ids = protocol_documents()
        missing_score = deepcopy(scores)
        missing_score["scores"].pop()
        with self.assertRaisesRegex(
            BlindEvaluationInvalid,
            "BLIND_EVAL_SAMPLE_SET_MISMATCH",
        ):
            compile_blind_comparison(
                assignments,
                missing_score,
                allowed_case_ids=case_ids,
            )

        unpaired_assignments = deepcopy(assignments)
        removed = unpaired_assignments["assignments"].pop()
        unpaired_scores = deepcopy(scores)
        unpaired_scores["scores"] = [
            score
            for score in unpaired_scores["scores"]
            if score["sampleId"] != removed["sampleId"]
        ]
        with self.assertRaisesRegex(
            BlindEvaluationInvalid,
            "BLIND_EVAL_UNPAIRED_ASSIGNMENT",
        ):
            compile_blind_comparison(
                unpaired_assignments,
                unpaired_scores,
                allowed_case_ids=case_ids,
            )

    def test_case_coverage_and_score_scale_are_enforced(self):
        assignments, scores, case_ids = protocol_documents(count=19)
        with self.assertRaisesRegex(
            BlindEvaluationInvalid,
            "BLIND_EVAL_INSUFFICIENT_CASE_COVERAGE",
        ):
            compile_blind_comparison(
                assignments,
                scores,
                allowed_case_ids=case_ids,
            )

        assignments, scores, case_ids = protocol_documents()
        invalid_score = deepcopy(scores)
        invalid_score["scores"][0]["taskScore"] = 0.8
        with self.assertRaisesRegex(
            BlindEvaluationInvalid,
            "BLIND_EVAL_TASK_SCORE_INVALID",
        ):
            compile_blind_comparison(
                assignments,
                invalid_score,
                allowed_case_ids=case_ids,
            )


if __name__ == "__main__":
    unittest.main()
