from collections import defaultdict
from math import ceil, inf
from statistics import fmean


COMPARISON_VERSION = "agent-model-comparison-v1"
BASELINE_MODEL = "qwen3.5-flash"
CANDIDATE_MODEL = "qwen3.7-plus"
DOCUMENT_FIELDS = {"version", "baselineModel", "candidateModel", "runs"}
RUN_FIELDS = {
    "caseId",
    "trial",
    "model",
    "taskScore",
    "safetyPassed",
    "groundingPassed",
    "latencyMs",
    "costCny",
}


class ModelComparisonInvalid(ValueError):
    pass


def _number(record: dict, field: str, minimum: float, maximum: float) -> float:
    value = record.get(field)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < minimum
        or value > maximum
    ):
        raise ModelComparisonInvalid(f"{field} must be between {minimum} and {maximum}")
    return float(value)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * percentile) - 1)]


def evaluate_model_upgrade(
    document: dict,
    *,
    minimum_pairs: int = 20,
    minimum_quality_gain: float = 0.05,
    maximum_cost_ratio: float = 1.5,
    maximum_latency_ratio: float = 1.5,
) -> dict:
    if set(document) != DOCUMENT_FIELDS:
        raise ModelComparisonInvalid("comparison document fields must match the allowlist")
    if document.get("version") != COMPARISON_VERSION:
        raise ModelComparisonInvalid("unsupported comparison version")
    if document.get("baselineModel") != BASELINE_MODEL:
        raise ModelComparisonInvalid("baseline model must remain qwen3.5-flash")
    if document.get("candidateModel") != CANDIDATE_MODEL:
        raise ModelComparisonInvalid("candidate model must remain qwen3.7-plus")
    runs = document.get("runs")
    if not isinstance(runs, list):
        raise ModelComparisonInvalid("runs must be a list")

    indexed: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for record in runs:
        if not isinstance(record, dict):
            raise ModelComparisonInvalid("each run must be an object")
        if set(record) != RUN_FIELDS:
            raise ModelComparisonInvalid("run fields must match the content-free allowlist")
        case_id = record.get("caseId")
        trial = record.get("trial", 1)
        model = record.get("model")
        if not isinstance(case_id, str) or not case_id or len(case_id) > 100:
            raise ModelComparisonInvalid("caseId must be a non-empty bounded string")
        if not isinstance(trial, int) or isinstance(trial, bool) or not 1 <= trial <= 20:
            raise ModelComparisonInvalid("trial must be between 1 and 20")
        if model not in {BASELINE_MODEL, CANDIDATE_MODEL}:
            raise ModelComparisonInvalid("run model is outside the approved comparison")
        if model in indexed[(case_id, trial)]:
            raise ModelComparisonInvalid("duplicate case, trial, and model")
        if not isinstance(record.get("safetyPassed"), bool):
            raise ModelComparisonInvalid("safetyPassed must be boolean")
        if not isinstance(record.get("groundingPassed"), bool):
            raise ModelComparisonInvalid("groundingPassed must be boolean")
        indexed[(case_id, trial)][model] = {
            "taskScore": _number(record, "taskScore", 0, 1),
            "safetyPassed": record["safetyPassed"],
            "groundingPassed": record["groundingPassed"],
            "latencyMs": _number(record, "latencyMs", 0, 600_000),
            "costCny": _number(record, "costCny", 0, 100),
        }

    pairs = [
        pair
        for pair in indexed.values()
        if BASELINE_MODEL in pair and CANDIDATE_MODEL in pair
    ]
    baseline = [pair[BASELINE_MODEL] for pair in pairs]
    candidate = [pair[CANDIDATE_MODEL] for pair in pairs]

    def summary(records: list[dict]) -> dict:
        if not records:
            return {
                "meanTaskScore": 0,
                "safetyFailures": 0,
                "groundingFailures": 0,
                "meanCostCny": 0,
                "latencyP95Ms": 0,
            }
        return {
            "meanTaskScore": round(fmean(item["taskScore"] for item in records), 6),
            "safetyFailures": sum(not item["safetyPassed"] for item in records),
            "groundingFailures": sum(not item["groundingPassed"] for item in records),
            "meanCostCny": round(fmean(item["costCny"] for item in records), 8),
            "latencyP95Ms": round(
                _percentile([item["latencyMs"] for item in records], 0.95),
                2,
            ),
        }

    baseline_summary = summary(baseline)
    candidate_summary = summary(candidate)
    quality_gain = (
        candidate_summary["meanTaskScore"] - baseline_summary["meanTaskScore"]
    )
    baseline_cost = baseline_summary["meanCostCny"]
    baseline_latency = baseline_summary["latencyP95Ms"]
    cost_ratio = (
        candidate_summary["meanCostCny"] / baseline_cost
        if baseline_cost > 0
        else 1
        if candidate_summary["meanCostCny"] == 0
        else inf
    )
    latency_ratio = (
        candidate_summary["latencyP95Ms"] / baseline_latency
        if baseline_latency > 0
        else 1
        if candidate_summary["latencyP95Ms"] == 0
        else inf
    )

    reasons: list[str] = []
    if len(pairs) < minimum_pairs:
        reasons.append("INSUFFICIENT_PAIRED_CASES")
    if candidate_summary["safetyFailures"]:
        reasons.append("CANDIDATE_SAFETY_FAILURE")
    if candidate_summary["groundingFailures"]:
        reasons.append("CANDIDATE_GROUNDING_FAILURE")
    if quality_gain < minimum_quality_gain:
        reasons.append("QUALITY_GAIN_NOT_MATERIAL")
    if cost_ratio > maximum_cost_ratio:
        reasons.append("COST_RATIO_TOO_HIGH")
    if latency_ratio > maximum_latency_ratio:
        reasons.append("LATENCY_RATIO_TOO_HIGH")

    eligible = not reasons
    return {
        "version": COMPARISON_VERSION,
        "decision": (
            "ELIGIBLE_FOR_5_PERCENT_REVIEW"
            if eligible
            else "KEEP_FLASH_0_PERCENT"
        ),
        "automaticRoutingChange": False,
        "pairedRunCount": len(pairs),
        "baseline": {"model": BASELINE_MODEL, **baseline_summary},
        "candidate": {"model": CANDIDATE_MODEL, **candidate_summary},
        "comparison": {
            "qualityGain": round(quality_gain, 6),
            "costRatio": round(cost_ratio, 6) if cost_ratio != inf else None,
            "latencyRatio": round(latency_ratio, 6) if latency_ratio != inf else None,
        },
        "thresholds": {
            "minimumPairs": minimum_pairs,
            "minimumQualityGain": minimum_quality_gain,
            "maximumCostRatio": maximum_cost_ratio,
            "maximumLatencyRatio": maximum_latency_ratio,
        },
        "reasons": reasons,
        "meta": {
            "containsPrompts": False,
            "containsResponses": False,
            "requiresHumanApproval": True,
        },
    }
