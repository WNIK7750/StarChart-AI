from collections import Counter
from hashlib import sha256
import json


MANIFEST_SCHEMA_VERSION = "agent-evaluation-manifest-v1"
SUITE_ID = "agent-phase1"
SUITE_VERSION = "agent-phase1-v1"
EXPECTED_CASE_COUNT = 30
EXPECTED_ROUTING_COUNT = 20
EXPECTED_OUTPUT_COUNT = 10
REQUIRED_INTENTS = {
    "qa",
    "navigation",
    "tool_recommendation",
    "learning_plan",
    "workflow_generation",
}
REQUIRED_REJECTION_CLASSES = {
    "link",
    "domain",
    "ip_address",
    "fabricated_citation",
    "secret_like_content",
    "html",
}
ROUTING_FIELDS = {
    "id",
    "message",
    "pageContext",
    "expectedIntent",
    "expectedQuery",
    "expectedCapabilities",
}
OUTPUT_FIELDS = {
    "id",
    "answer",
    "expectedAllowed",
    "expectedError",
    "allowedDottedTerms",
}
FAILURE_CLASSES = (
    "EVAL_MANIFEST_SCHEMA_INVALID",
    "EVAL_MANIFEST_DUPLICATE_CASE_ID",
    "EVAL_MANIFEST_CASE_COUNT_MISMATCH",
    "EVAL_MANIFEST_CATEGORY_COVERAGE_MISSING",
    "EVAL_MANIFEST_EXPECTATION_INVALID",
    "EVAL_ARTIFACT_STALE",
)


class EvaluationManifestInvalid(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _fail(code: str, message: str) -> None:
    raise EvaluationManifestInvalid(code, message)


def _bounded_id(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 100:
        _fail("EVAL_MANIFEST_SCHEMA_INVALID", "case id must be a bounded string")
    return value


def _validate_fields(case: dict, allowed: set[str], case_id: str) -> None:
    unknown = set(case) - allowed
    if unknown:
        _fail(
            "EVAL_MANIFEST_SCHEMA_INVALID",
            f"{case_id} contains unsupported fields: {sorted(unknown)}",
        )


def _semantic_sha256(document: dict) -> str:
    canonical = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def build_evaluation_manifest(document: dict) -> dict:
    if not isinstance(document, dict) or set(document) != {
        "version",
        "routingCases",
        "outputCases",
    }:
        _fail("EVAL_MANIFEST_SCHEMA_INVALID", "suite fields must match the allowlist")
    if document.get("version") != SUITE_VERSION:
        _fail("EVAL_MANIFEST_SCHEMA_INVALID", "suite version is unsupported")

    routing_cases = document.get("routingCases")
    output_cases = document.get("outputCases")
    if not isinstance(routing_cases, list) or not isinstance(output_cases, list):
        _fail("EVAL_MANIFEST_SCHEMA_INVALID", "case groups must be lists")
    if (
        len(routing_cases) != EXPECTED_ROUTING_COUNT
        or len(output_cases) != EXPECTED_OUTPUT_COUNT
        or len(routing_cases) + len(output_cases) != EXPECTED_CASE_COUNT
    ):
        _fail(
            "EVAL_MANIFEST_CASE_COUNT_MISMATCH",
            "suite must contain 20 routing and 10 provider-output cases",
        )

    case_ids: set[str] = set()
    intent_counts: Counter[str] = Counter()
    for case in routing_cases:
        if not isinstance(case, dict):
            _fail("EVAL_MANIFEST_SCHEMA_INVALID", "routing case must be an object")
        case_id = _bounded_id(case.get("id"))
        _validate_fields(case, ROUTING_FIELDS, case_id)
        if case_id in case_ids:
            _fail("EVAL_MANIFEST_DUPLICATE_CASE_ID", case_id)
        case_ids.add(case_id)
        intent = case.get("expectedIntent")
        if intent not in REQUIRED_INTENTS:
            _fail(
                "EVAL_MANIFEST_EXPECTATION_INVALID",
                f"{case_id} has an unsupported expected intent",
            )
        if not isinstance(case.get("message"), str) or not case["message"].strip():
            _fail("EVAL_MANIFEST_SCHEMA_INVALID", f"{case_id} has no message")
        if not isinstance(case.get("expectedQuery"), str):
            _fail("EVAL_MANIFEST_SCHEMA_INVALID", f"{case_id} has no expected query")
        capabilities = case.get("expectedCapabilities")
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or any(not isinstance(item, str) or not item for item in capabilities)
        ):
            _fail(
                "EVAL_MANIFEST_EXPECTATION_INVALID",
                f"{case_id} has invalid capability expectations",
            )
        intent_counts[intent] += 1

    allowed_count = 0
    rejected_count = 0
    rejection_counts: Counter[str] = Counter()
    for case in output_cases:
        if not isinstance(case, dict):
            _fail("EVAL_MANIFEST_SCHEMA_INVALID", "output case must be an object")
        case_id = _bounded_id(case.get("id"))
        _validate_fields(case, OUTPUT_FIELDS, case_id)
        if case_id in case_ids:
            _fail("EVAL_MANIFEST_DUPLICATE_CASE_ID", case_id)
        case_ids.add(case_id)
        if not isinstance(case.get("answer"), str) or not case["answer"]:
            _fail("EVAL_MANIFEST_SCHEMA_INVALID", f"{case_id} has no answer")
        expected_allowed = case.get("expectedAllowed")
        if not isinstance(expected_allowed, bool):
            _fail(
                "EVAL_MANIFEST_EXPECTATION_INVALID",
                f"{case_id} expectedAllowed must be boolean",
            )
        expected_error = case.get("expectedError")
        if expected_allowed:
            if expected_error is not None:
                _fail(
                    "EVAL_MANIFEST_EXPECTATION_INVALID",
                    f"{case_id} cannot expect an error when allowed",
                )
            allowed_count += 1
        else:
            if expected_error not in REQUIRED_REJECTION_CLASSES:
                _fail(
                    "EVAL_MANIFEST_EXPECTATION_INVALID",
                    f"{case_id} has an unsupported rejection class",
                )
            rejected_count += 1
            rejection_counts[expected_error] += 1

    if set(intent_counts) != REQUIRED_INTENTS:
        _fail(
            "EVAL_MANIFEST_CATEGORY_COVERAGE_MISSING",
            "routing intent coverage is incomplete",
        )
    if set(rejection_counts) != REQUIRED_REJECTION_CLASSES:
        _fail(
            "EVAL_MANIFEST_CATEGORY_COVERAGE_MISSING",
            "provider-output rejection coverage is incomplete",
        )

    return {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "suiteId": SUITE_ID,
        "suiteVersion": SUITE_VERSION,
        "sourceSemanticSha256": _semantic_sha256(document),
        "caseCount": len(case_ids),
        "groups": {
            "routing": {
                "caseCount": len(routing_cases),
                "intentCounts": dict(sorted(intent_counts.items())),
            },
            "providerOutput": {
                "caseCount": len(output_cases),
                "allowedCount": allowed_count,
                "rejectedCount": rejected_count,
                "rejectionClassCounts": dict(sorted(rejection_counts.items())),
            },
        },
        "failureClasses": list(FAILURE_CLASSES),
        "privacy": {
            "containsCaseIds": False,
            "containsMessages": False,
            "containsAnswers": False,
        },
    }
