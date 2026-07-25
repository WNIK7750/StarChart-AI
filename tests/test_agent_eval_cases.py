import json
from copy import deepcopy
from pathlib import Path
import unittest

from app.agent.evaluation_manifest import (
    EvaluationManifestInvalid,
    build_evaluation_manifest,
)
from app.agent.evaluator import validate_provider_answer
from app.agent.router import classify_intent
from app.agent.schemas import AgentChatRequest
from app.agent.service import agent_retrieval_query, plan_read_capabilities


CASES_PATH = Path(__file__).parent / "fixtures" / "agent_phase1_cases.json"


class AgentPhase1EvalCasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    def test_versioned_routing_and_capability_cases(self):
        self.assertEqual("agent-phase1-v1", self.cases["version"])
        for case in self.cases["routingCases"]:
            with self.subTest(case=case["id"]):
                intent = classify_intent(case["message"])
                request = AgentChatRequest(
                    message=case["message"],
                    pageContext=case.get("pageContext", {}),
                )
                self.assertEqual(case["expectedIntent"], intent)
                self.assertEqual(
                    case["expectedQuery"],
                    agent_retrieval_query(case["message"], intent, request.pageContext),
                )
                self.assertEqual(
                    set(case["expectedCapabilities"]),
                    plan_read_capabilities(request, intent),
                )

    def test_versioned_provider_output_cases(self):
        for case in self.cases["outputCases"]:
            with self.subTest(case=case["id"]):
                if case["expectedAllowed"]:
                    self.assertEqual(
                        case["answer"],
                        validate_provider_answer(
                            case["answer"],
                            2000,
                            allowed_dotted_terms=set(case.get("allowedDottedTerms", [])),
                        ),
                    )
                    continue
                with self.assertRaisesRegex(ValueError, case["expectedError"]):
                    validate_provider_answer(
                        case["answer"],
                        2000,
                        allowed_dotted_terms=set(case.get("allowedDottedTerms", [])),
                    )

    def test_content_free_manifest_is_stable_and_complete(self):
        manifest = build_evaluation_manifest(self.cases)
        rendered = json.dumps(manifest, ensure_ascii=False)

        self.assertEqual("agent-evaluation-manifest-v1", manifest["schemaVersion"])
        self.assertEqual(30, manifest["caseCount"])
        self.assertEqual(20, manifest["groups"]["routing"]["caseCount"])
        self.assertEqual(10, manifest["groups"]["providerOutput"]["caseCount"])
        self.assertEqual(6, manifest["groups"]["providerOutput"]["rejectedCount"])
        self.assertFalse(manifest["privacy"]["containsMessages"])
        self.assertFalse(manifest["privacy"]["containsAnswers"])
        self.assertNotIn("RAG是什么", rendered)
        self.assertNotIn("https://", rendered)

    def test_manifest_classifies_duplicate_and_incomplete_suites(self):
        duplicate = deepcopy(self.cases)
        duplicate["outputCases"][0]["id"] = duplicate["routingCases"][0]["id"]
        with self.assertRaisesRegex(
            EvaluationManifestInvalid,
            "EVAL_MANIFEST_DUPLICATE_CASE_ID",
        ):
            build_evaluation_manifest(duplicate)

        incomplete = deepcopy(self.cases)
        incomplete["routingCases"].pop()
        with self.assertRaisesRegex(
            EvaluationManifestInvalid,
            "EVAL_MANIFEST_CASE_COUNT_MISMATCH",
        ):
            build_evaluation_manifest(incomplete)


if __name__ == "__main__":
    unittest.main()
