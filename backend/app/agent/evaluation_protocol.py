from collections import defaultdict
import re

from app.agent.model_gate import (
    BASELINE_MODEL,
    CANDIDATE_MODEL,
    COMPARISON_VERSION,
)


ASSIGNMENT_VERSION = "agent-blind-assignment-v1"
SCORES_VERSION = "agent-blind-scores-v1"
RUBRIC_VERSION = "agent-model-rubric-v1"
SUITE_VERSION = "agent-phase1-v1"
PROTOCOL_MANIFEST_VERSION = "agent-blind-protocol-manifest-v1"
MINIMUM_UNIQUE_CASES = 20
MINIMUM_TRIAL = 1
MAXIMUM_TRIAL = 20
MAXIMUM_LATENCY_MS = 600_000
MAXIMUM_COST_CNY = 100
ASSIGNMENT_DOCUMENT_FIELDS = {
    "version",
    "suiteVersion",
    "rubricVersion",
    "assignments",
}
ASSIGNMENT_FIELDS = {
    "sampleId",
    "caseId",
    "trial",
    "model",
    "latencyMs",
    "costCny",
}
SCORES_DOCUMENT_FIELDS = {"version", "rubricVersion", "scores"}
SCORE_FIELDS = {
    "sampleId",
    "taskScore",
    "safetyPassed",
    "groundingPassed",
}
TASK_SCORE_VALUES = {0.0, 0.25, 0.5, 0.75, 1.0}
SAMPLE_ID_PATTERN = re.compile(r"^sample_[A-Za-z0-9_-]{8,64}$")
FAILURE_CLASSES = (
    "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
    "BLIND_EVAL_SCORE_SCHEMA_INVALID",
    "BLIND_EVAL_METRIC_INVALID",
    "BLIND_EVAL_SAMPLE_ID_INVALID",
    "BLIND_EVAL_DUPLICATE_SAMPLE_ID",
    "BLIND_EVAL_UNKNOWN_CASE",
    "BLIND_EVAL_TRIAL_INVALID",
    "BLIND_EVAL_MODEL_INVALID",
    "BLIND_EVAL_DUPLICATE_MODEL_ASSIGNMENT",
    "BLIND_EVAL_TASK_SCORE_INVALID",
    "BLIND_EVAL_SAMPLE_SET_MISMATCH",
    "BLIND_EVAL_UNPAIRED_ASSIGNMENT",
    "BLIND_EVAL_INSUFFICIENT_CASE_COVERAGE",
    "BLIND_EVAL_PROTOCOL_ARTIFACT_STALE",
)
SECOND_REVIEW_TRIGGERS = (
    "SAFETY_FAILURE",
    "GROUNDING_FAILURE",
    "BOUNDARY_SCORE",
    "ELIGIBLE_FOR_5_PERCENT_REVIEW",
)


class BlindEvaluationInvalid(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _fail(code: str, message: str) -> None:
    if code not in FAILURE_CLASSES:
        raise RuntimeError(f"undeclared blind evaluation failure class: {code}")
    raise BlindEvaluationInvalid(code, message)


def build_blind_protocol_manifest() -> dict:
    return {
        "schemaVersion": PROTOCOL_MANIFEST_VERSION,
        "suiteVersion": SUITE_VERSION,
        "rubricVersion": RUBRIC_VERSION,
        "comparisonVersion": COMPARISON_VERSION,
        "documentVersions": {
            "assignment": ASSIGNMENT_VERSION,
            "scores": SCORES_VERSION,
        },
        "approvedModels": [BASELINE_MODEL, CANDIDATE_MODEL],
        "documentFields": {
            "assignment": sorted(ASSIGNMENT_DOCUMENT_FIELDS),
            "assignmentRecord": sorted(ASSIGNMENT_FIELDS),
            "scores": sorted(SCORES_DOCUMENT_FIELDS),
            "scoreRecord": sorted(SCORE_FIELDS),
        },
        "limits": {
            "minimumUniqueCases": MINIMUM_UNIQUE_CASES,
            "trialMinimum": MINIMUM_TRIAL,
            "trialMaximum": MAXIMUM_TRIAL,
            "latencyMaximumMs": MAXIMUM_LATENCY_MS,
            "costMaximumCny": MAXIMUM_COST_CNY,
            "taskScoreValues": sorted(TASK_SCORE_VALUES),
            "sampleIdPattern": SAMPLE_ID_PATTERN.pattern,
        },
        "reviewPolicy": {
            "primaryRaterCount": 1,
            "secondReviewTriggers": list(SECOND_REVIEW_TRIGGERS),
        },
        "failureClasses": list(FAILURE_CLASSES),
        "privacy": {
            "scoreContainsModel": False,
            "scoreContainsPrompt": False,
            "scoreContainsResponse": False,
            "scoreContainsLatencyOrCost": False,
            "containsCaseContent": False,
        },
    }


def _number(
    record: dict,
    field: str,
    minimum: float,
    maximum: float,
) -> float:
    value = record.get(field)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < minimum
        or value > maximum
    ):
        _fail(
            "BLIND_EVAL_METRIC_INVALID",
            f"{field} must be between {minimum} and {maximum}",
        )
    return float(value)


def _sample_id(value: object) -> str:
    if not isinstance(value, str) or not SAMPLE_ID_PATTERN.fullmatch(value):
        _fail(
            "BLIND_EVAL_SAMPLE_ID_INVALID",
            "sampleId must be opaque and match the approved format",
        )
    return value


def compile_blind_comparison(
    assignment_document: dict,
    scores_document: dict,
    *,
    allowed_case_ids: set[str],
    minimum_unique_cases: int = MINIMUM_UNIQUE_CASES,
) -> dict:
    if not isinstance(assignment_document, dict) or set(
        assignment_document
    ) != ASSIGNMENT_DOCUMENT_FIELDS:
        _fail(
            "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
            "assignment document fields must match the allowlist",
        )
    if assignment_document.get("version") != ASSIGNMENT_VERSION:
        _fail(
            "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
            "assignment version is unsupported",
        )
    if assignment_document.get("suiteVersion") != SUITE_VERSION:
        _fail(
            "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
            "suite version is unsupported",
        )
    if assignment_document.get("rubricVersion") != RUBRIC_VERSION:
        _fail(
            "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
            "rubric version is unsupported",
        )
    assignments = assignment_document.get("assignments")
    if not isinstance(assignments, list):
        _fail(
            "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
            "assignments must be a list",
        )

    if not isinstance(scores_document, dict) or set(
        scores_document
    ) != SCORES_DOCUMENT_FIELDS:
        _fail(
            "BLIND_EVAL_SCORE_SCHEMA_INVALID",
            "score document fields must match the content-free allowlist",
        )
    if scores_document.get("version") != SCORES_VERSION:
        _fail("BLIND_EVAL_SCORE_SCHEMA_INVALID", "score version is unsupported")
    if scores_document.get("rubricVersion") != RUBRIC_VERSION:
        _fail("BLIND_EVAL_SCORE_SCHEMA_INVALID", "rubric version is unsupported")
    scores = scores_document.get("scores")
    if not isinstance(scores, list):
        _fail("BLIND_EVAL_SCORE_SCHEMA_INVALID", "scores must be a list")

    assignments_by_sample: dict[str, dict] = {}
    pair_models: dict[tuple[str, int], set[str]] = defaultdict(set)
    for record in assignments:
        if not isinstance(record, dict) or set(record) != ASSIGNMENT_FIELDS:
            _fail(
                "BLIND_EVAL_ASSIGNMENT_SCHEMA_INVALID",
                "assignment fields must match the allowlist",
            )
        sample_id = _sample_id(record.get("sampleId"))
        if sample_id in assignments_by_sample:
            _fail("BLIND_EVAL_DUPLICATE_SAMPLE_ID", sample_id)
        case_id = record.get("caseId")
        if case_id not in allowed_case_ids:
            _fail(
                "BLIND_EVAL_UNKNOWN_CASE",
                "assignment references a case outside the approved suite",
            )
        trial = record.get("trial")
        if (
            not isinstance(trial, int)
            or isinstance(trial, bool)
            or not MINIMUM_TRIAL <= trial <= MAXIMUM_TRIAL
        ):
            _fail("BLIND_EVAL_TRIAL_INVALID", "trial must be between 1 and 20")
        model = record.get("model")
        if model not in {BASELINE_MODEL, CANDIDATE_MODEL}:
            _fail(
                "BLIND_EVAL_MODEL_INVALID",
                "assignment model is outside the approved comparison",
            )
        pair_key = (case_id, trial)
        if model in pair_models[pair_key]:
            _fail(
                "BLIND_EVAL_DUPLICATE_MODEL_ASSIGNMENT",
                "case and trial contain a duplicate model",
            )
        pair_models[pair_key].add(model)
        assignments_by_sample[sample_id] = {
            "caseId": case_id,
            "trial": trial,
            "model": model,
            "latencyMs": _number(
                record,
                "latencyMs",
                0,
                MAXIMUM_LATENCY_MS,
            ),
            "costCny": _number(record, "costCny", 0, MAXIMUM_COST_CNY),
        }

    scores_by_sample: dict[str, dict] = {}
    for record in scores:
        if not isinstance(record, dict) or set(record) != SCORE_FIELDS:
            _fail(
                "BLIND_EVAL_SCORE_SCHEMA_INVALID",
                "score fields must match the content-free allowlist",
            )
        sample_id = _sample_id(record.get("sampleId"))
        if sample_id in scores_by_sample:
            _fail("BLIND_EVAL_DUPLICATE_SAMPLE_ID", sample_id)
        task_score = record.get("taskScore")
        if (
            not isinstance(task_score, (int, float))
            or isinstance(task_score, bool)
            or float(task_score) not in TASK_SCORE_VALUES
        ):
            _fail(
                "BLIND_EVAL_TASK_SCORE_INVALID",
                "taskScore must use the approved five-point scale",
            )
        if not isinstance(record.get("safetyPassed"), bool):
            _fail(
                "BLIND_EVAL_SCORE_SCHEMA_INVALID",
                "safetyPassed must be boolean",
            )
        if not isinstance(record.get("groundingPassed"), bool):
            _fail(
                "BLIND_EVAL_SCORE_SCHEMA_INVALID",
                "groundingPassed must be boolean",
            )
        scores_by_sample[sample_id] = {
            "taskScore": float(task_score),
            "safetyPassed": record["safetyPassed"],
            "groundingPassed": record["groundingPassed"],
        }

    if set(assignments_by_sample) != set(scores_by_sample):
        _fail(
            "BLIND_EVAL_SAMPLE_SET_MISMATCH",
            "every assignment must have exactly one blind score",
        )
    approved_models = {BASELINE_MODEL, CANDIDATE_MODEL}
    if any(models != approved_models for models in pair_models.values()):
        _fail(
            "BLIND_EVAL_UNPAIRED_ASSIGNMENT",
            "each case and trial must contain both approved models",
        )
    unique_cases = {case_id for case_id, _trial in pair_models}
    if len(unique_cases) < minimum_unique_cases:
        _fail(
            "BLIND_EVAL_INSUFFICIENT_CASE_COVERAGE",
            f"at least {minimum_unique_cases} unique cases are required",
        )

    model_order = {BASELINE_MODEL: 0, CANDIDATE_MODEL: 1}
    runs = []
    for sample_id, assignment in assignments_by_sample.items():
        score = scores_by_sample[sample_id]
        runs.append({**assignment, **score})
    runs.sort(
        key=lambda item: (
            item["caseId"],
            item["trial"],
            model_order[item["model"]],
        )
    )
    return {
        "version": COMPARISON_VERSION,
        "baselineModel": BASELINE_MODEL,
        "candidateModel": CANDIDATE_MODEL,
        "runs": runs,
    }
