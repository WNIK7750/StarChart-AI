from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SNAPSHOT_KEYS = {
    "targetCommit",
    "archiveSha256",
    "authReportSha256",
    "server",
    "publicRoutes",
    "runtimePolicy",
}
AUTH_KEYS = {
    "schemaVersion",
    "validationStatus",
    "checksRecorded",
    "passedChecks",
    "failedChecks",
    "checks",
    "sensitiveDataRecorded",
}
AUTH_CHECK_KEYS = {
    "passed",
    "statusCode",
    "elapsedMs",
    "errorType",
}
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CHECK_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class ValidationInputError(ValueError):
    pass


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationInputError(f"{label} must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValidationInputError(f"{label} must be an object")
    return payload


def _exact_keys(payload: dict[str, Any], expected: set[str], label: str) -> None:
    if set(payload) != expected:
        raise ValidationInputError(f"{label} has an unexpected schema")


def _true(value: object, label: str) -> None:
    if value is not True:
        raise ValidationInputError(f"{label} must be true")


def _non_negative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationInputError(f"{label} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValidationInputError(f"{label} must be finite and non-negative")
    return numeric


def _validate_server(server: object) -> dict[str, Any]:
    if not isinstance(server, dict):
        raise ValidationInputError("server must be an object")
    _exact_keys(
        server,
        {
            "nginxActive",
            "nginxSyntaxValid",
            "httpTestServiceActive",
            "deterministicSmokePassed",
            "portBindings",
            "database",
            "backup",
        },
        "server",
    )
    for name in (
        "nginxActive",
        "nginxSyntaxValid",
        "httpTestServiceActive",
        "deterministicSmokePassed",
    ):
        _true(server[name], f"server.{name}")

    ports = server["portBindings"]
    if ports != {
        "legacy8000": "0.0.0.0",
        "httpTest8001": "127.0.0.1",
        "providerPreview8002": "closed",
    }:
        raise ValidationInputError("port bindings do not match the approved topology")

    database = server["database"]
    if database != {
        "accountCount": 1,
        "mode": "0600",
        "owner": "dedicated-http-test-service-account",
        "isolatedFromLegacyDatabase": True,
    }:
        raise ValidationInputError("database isolation evidence is incomplete")

    backup = server["backup"]
    if backup != {
        "archivePresent": True,
        "gzipIntegrityPassed": True,
        "restoreExercise": "not_run",
    }:
        raise ValidationInputError("backup evidence must not imply a restore exercise")
    return server


def _validate_routes(routes: object) -> list[dict[str, Any]]:
    if not isinstance(routes, list) or not routes:
        raise ValidationInputError("publicRoutes must be a non-empty array")
    validated: list[dict[str, Any]] = []
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            raise ValidationInputError(f"publicRoutes[{index}] must be an object")
        _exact_keys(
            route,
            {"path", "statusCode", "elapsedMs", "downloadBytes"},
            f"publicRoutes[{index}]",
        )
        if (
            not isinstance(route["path"], str)
            or not route["path"].startswith("/")
            or "://" in route["path"]
        ):
            raise ValidationInputError(f"publicRoutes[{index}].path must be relative")
        if route["statusCode"] != 200:
            raise ValidationInputError(f"publicRoutes[{index}] did not return 200")
        elapsed = _non_negative_number(
            route["elapsedMs"],
            f"publicRoutes[{index}].elapsedMs",
        )
        if (
            isinstance(route["downloadBytes"], bool)
            or not isinstance(route["downloadBytes"], int)
            or route["downloadBytes"] < 0
        ):
            raise ValidationInputError(
                f"publicRoutes[{index}].downloadBytes must be non-negative"
            )
        validated.append(
            {
                "path": route["path"],
                "statusCode": 200,
                "elapsedMs": elapsed,
                "downloadBytes": route["downloadBytes"],
            }
        )
    return validated


def _validate_runtime_policy(policy: object) -> dict[str, Any]:
    expected = {
        "deploymentProfile": "http_test",
        "publicBasePath": "/StarChart-AI",
        "registration": False,
        "recovery": False,
        "identityChanges": False,
        "privacyWrites": False,
        "guestChat": True,
        "authenticatedSessions": True,
    }
    if policy != expected:
        raise ValidationInputError("runtime policy does not match HTTP-test boundaries")
    return expected


def _validate_auth_report(report: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(report, AUTH_KEYS, "auth report")
    if (
        report["schemaVersion"] != 1
        or report["validationStatus"] != "passed"
        or report["sensitiveDataRecorded"] is not False
    ):
        raise ValidationInputError("auth report is not a passing redacted report")
    checks = report["checks"]
    if not isinstance(checks, dict) or not checks:
        raise ValidationInputError("auth report checks must be non-empty")
    projected: dict[str, dict[str, int | float]] = {}
    for name, check in checks.items():
        if not isinstance(name, str) or not CHECK_NAME_PATTERN.fullmatch(name):
            raise ValidationInputError("auth report check name is invalid")
        if not isinstance(check, dict):
            raise ValidationInputError(f"auth check {name} must be an object")
        _exact_keys(check, AUTH_CHECK_KEYS, f"auth check {name}")
        if check["passed"] is not True or check["errorType"] is not None:
            raise ValidationInputError(f"auth check {name} did not pass")
        if (
            isinstance(check["statusCode"], bool)
            or not isinstance(check["statusCode"], int)
            or not 100 <= check["statusCode"] <= 599
        ):
            raise ValidationInputError(f"auth check {name} has an invalid status")
        elapsed = _non_negative_number(check["elapsedMs"], f"auth check {name}")
        projected[name] = {
            "statusCode": check["statusCode"],
            "elapsedMs": elapsed,
        }

    count = len(projected)
    if (
        report["checksRecorded"] != count
        or report["passedChecks"] != count
        or report["failedChecks"] != 0
    ):
        raise ValidationInputError("auth report counts are inconsistent")
    return {
        "validationStatus": "passed",
        "checksRecorded": count,
        "passedChecks": count,
        "failedChecks": 0,
        "checks": projected,
    }


def build_validation(
    snapshot: dict[str, Any],
    auth_report: dict[str, Any],
) -> dict[str, Any]:
    _exact_keys(snapshot, SNAPSHOT_KEYS, "snapshot")
    if not COMMIT_PATTERN.fullmatch(str(snapshot["targetCommit"])):
        raise ValidationInputError("targetCommit must be a full lowercase git SHA")
    for name in ("archiveSha256", "authReportSha256"):
        if not SHA256_PATTERN.fullmatch(str(snapshot[name])):
            raise ValidationInputError(f"{name} must be a lowercase SHA-256")

    authenticated_flow = _validate_auth_report(auth_report)
    authenticated_flow["reportSha256"] = snapshot["authReportSha256"]
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "target": "authorized-http-test-host",
        "targetCommit": snapshot["targetCommit"],
        "release": {
            "archiveSha256": snapshot["archiveSha256"],
            "currentReleaseMatchesTarget": True,
            "immutableReleaseDirectory": True,
        },
        "server": _validate_server(snapshot["server"]),
        "publicRoutes": _validate_routes(snapshot["publicRoutes"]),
        "runtimePolicy": _validate_runtime_policy(snapshot["runtimePolicy"]),
        "authenticatedFlow": authenticated_flow,
        "notRun": {
            "providerPreview": "not_run",
            "providerPaidRequest": "not_run",
            "https": "not_run",
            "backupRestore": "not_run",
            "rollbackExercise": "not_run",
            "capacity": "not_run",
            "complianceSignoff": "not_run",
            "externalProductionSignoff": "not_run",
        },
        "conclusions": {
            "localRemediationCandidate": "go",
            "httpTestDeployment": "go",
            "providerPreview": "not_run",
            "productionRelease": "no_go",
        },
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
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build redacted HTTP-test server validation evidence."
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--auth-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        snapshot = _load_object(args.snapshot.resolve(), "snapshot")
        auth_report = _load_object(args.auth_report.resolve(), "auth report")
        atomic_write_json(
            args.output.resolve(),
            build_validation(snapshot, auth_report),
        )
    except ValidationInputError as exc:
        print(f"HTTP_TEST_SERVER_VALIDATION_REJECTED: {exc}")
        return 1
    print("HTTP-test server validation evidence generated from redacted inputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
