from datetime import datetime, timezone
from hashlib import sha256
import json

from app.agent.model_gate import evaluate_model_upgrade


DECISION_REPORT_VERSION = "agent-model-decision-report-v1"
ARCHIVE_METADATA_VERSION = "agent-model-decision-archive-v1"


def _canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def render_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def build_decision_report(source: bytes) -> dict:
    document = json.loads(source.decode("utf-8"))
    return {
        "schemaVersion": DECISION_REPORT_VERSION,
        "sourceSemanticSha256": sha256(_canonical_bytes(document)).hexdigest(),
        "evaluation": evaluate_model_upgrade(document),
    }


def build_archive_metadata(
    source: bytes,
    decision_report: dict,
    *,
    generated_at: datetime | None = None,
) -> dict:
    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("generated_at must include a timezone")
    return {
        "schemaVersion": ARCHIVE_METADATA_VERSION,
        "sourceByteSha256": sha256(source).hexdigest(),
        "decisionReportSha256": sha256(_canonical_bytes(decision_report)).hexdigest(),
        "generatedAt": timestamp.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }
