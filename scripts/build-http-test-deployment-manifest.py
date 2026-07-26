from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CHECK_NAMES = (
    "runtime",
    "policy",
    "agentHistory",
    "guestAgent",
    "frontend",
    "overlay",
    "release",
)
RESULT_KEYS = {
    "schemaVersion",
    "runId",
    "name",
    "passed",
    "count",
    "startedAt",
    "finishedAt",
}
EXTERNAL_VALIDATION = {
    "serverDeployment": "not_run",
    "providerPreview": "not_run",
    "https": "not_run",
    "backupRestore": "not_run",
    "rollback": "not_run",
}
COMMIT_PATTERN = re.compile(r"^(?:WORKTREE|[0-9a-f]{7,40})$")


class ManifestInputError(ValueError):
    pass


def _parse_utc_timestamp(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ManifestInputError(f"{field} must be a UTC ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ManifestInputError(f"{field} must be a UTC ISO-8601 timestamp") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ManifestInputError(f"{field} must use UTC")
    return value


def _load_result(path: Path, expected_name: str, run_id: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestInputError(f"invalid structured result: {expected_name}") from exc
    if not isinstance(payload, dict) or set(payload) != RESULT_KEYS:
        raise ManifestInputError(f"unexpected structured result schema: {expected_name}")
    if payload["schemaVersion"] != 1:
        raise ManifestInputError(f"unsupported structured result version: {expected_name}")
    if payload["runId"] != run_id:
        raise ManifestInputError(f"result does not belong to this run: {expected_name}")
    if payload["name"] != expected_name:
        raise ManifestInputError(f"result name mismatch: {expected_name}")
    if type(payload["passed"]) is not bool:
        raise ManifestInputError(f"passed must be boolean: {expected_name}")
    if type(payload["count"]) is not int or payload["count"] < 0:
        raise ManifestInputError(f"count must be a non-negative integer: {expected_name}")
    started = _parse_utc_timestamp(payload["startedAt"], "startedAt")
    finished = _parse_utc_timestamp(payload["finishedAt"], "finishedAt")
    if finished < started:
        raise ManifestInputError(f"result timestamps are reversed: {expected_name}")
    return payload


def build_manifest(
    results_dir: Path,
    run_id: str,
    source_commit: str,
) -> dict[str, Any]:
    if not run_id or len(run_id) > 128:
        raise ManifestInputError("run-id is required")
    if not COMMIT_PATTERN.fullmatch(source_commit):
        raise ManifestInputError("source-commit must be a git SHA or WORKTREE")

    checks: list[dict[str, Any]] = []
    for name in CHECK_NAMES:
        result = _load_result(results_dir / f"{name}.json", name, run_id)
        checks.append(
            {
                "name": name,
                "passed": result["passed"],
                "count": result["count"],
            }
        )
    if not all(check["passed"] for check in checks):
        failed = ", ".join(check["name"] for check in checks if not check["passed"])
        raise ManifestInputError(f"failed checks prevent evidence replacement: {failed}")

    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sourceCommit": source_commit,
        "checks": checks,
        "externalValidation": dict(EXTERNAL_VALIDATION),
        "containsSecrets": False,
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(rendered)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build content-free HTTP test deployment evidence."
    )
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_manifest(
            args.results_dir.resolve(),
            args.run_id,
            args.source_commit,
        )
        atomic_write_json(args.output.resolve(), manifest)
    except ManifestInputError as exc:
        print(f"HTTP_TEST_MANIFEST_REJECTED: {exc}")
        return 1
    print("HTTP test deployment manifest replaced from current structured results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
