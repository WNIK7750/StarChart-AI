from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any
from uuid import uuid4


RESULT_PREFIX = "AGENT_STAGE2_RESULT="
PROFILES = ("enabled", "rollback")


def _configure_environment(database_path: Path, profile: str) -> None:
    enabled = profile == "enabled"
    explicit_environment = {
        "AI_NAV_ENV": "test",
        "AI_NAV_DATABASE_PATH": str(database_path),
        "AI_NAV_SECRET_KEY": "agent-stage2-rehearsal-only-secret",
        "AI_NAV_CORS_ALLOW_ORIGINS": "http://127.0.0.1:8000",
        "AI_NAV_REFRESH_COOKIE_SECURE": "0",
        "AI_NAV_API_WORKERS": "1",
        "AI_NAV_AGENT_RUNTIME_STATE_BACKEND": "process_local",
        "AI_NAV_AGENT_PROVIDER": "deterministic",
        "AI_NAV_AGENT_PROVIDER_LIVE_ENABLED": "0",
        "AI_NAV_AGENT_PROVIDER_BASE_URL": "",
        "AI_NAV_AGENT_PROVIDER_API_KEY": "",
        "AI_NAV_AGENT_PROVIDER_ALLOWED_HOSTS": "",
        "AI_NAV_AGENT_PROVIDER_MODEL": "qwen3.5-flash",
        "AI_NAV_AGENT_PROVIDER_UPGRADE_MODEL": "qwen3.7-plus",
        "AI_NAV_AGENT_PROVIDER_UPGRADE_RATIO": "0",
        "AI_NAV_AGENT_STREAM_ENABLED": "1" if enabled else "0",
        "AI_NAV_AGENT_SESSIONS_ENABLED": "1" if enabled else "0",
        "RESET_DATABASE_ON_START": "0",
    }
    os.environ.update(explicit_environment)


def _assert_status(response: Any, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(
            f"{label} returned {response.status_code}, expected {expected}"
        )


def _parse_sse(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        data_lines = [
            line[6:]
            for line in block.splitlines()
            if line.startswith("data: ")
        ]
        if data_lines:
            events.append(json.loads("\n".join(data_lines)))
    return events


def _grant_admin(database_path: Path, username: str) -> None:
    with sqlite3.connect(database_path) as conn:
        user = conn.execute(
            "SELECT id FROM user_accounts WHERE username = ?",
            (username,),
        ).fetchone()
        if user is None:
            raise RuntimeError("Rehearsal user was not created")
        conn.execute(
            """
            INSERT OR IGNORE INTO user_role_assignments(user_id, role_id)
            SELECT ?, id FROM roles WHERE code = 'admin'
            """,
            (user[0],),
        )


def _runtime_is_bounded(runtime: dict[str, Any]) -> bool:
    serialized = json.dumps(runtime, ensure_ascii=False).lower()
    forbidden_fields = (
        "apikey",
        "api_key",
        "baseurl",
        "base_url",
        "allowedhosts",
        "allowed_hosts",
    )
    return not any(field in serialized for field in forbidden_fields)


async def _register_rehearsal_user(client: Any, database_path: Path) -> str:
    suffix = uuid4().hex[:12]
    username = f"agent_stage2_{suffix}"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "AgentStage2Qa123",
            "email": f"{username}@example.test",
            "displayName": "Agent Stage 2 QA",
            "privacyAccepted": True,
        },
    )
    _assert_status(response, 201, "register")
    access_token = response.json().get("accessToken")
    if not access_token:
        raise RuntimeError("Registration did not issue an access token")
    _grant_admin(database_path, username)
    return access_token


async def _run_enabled_profile(client: Any, headers: dict[str, str]) -> dict[str, Any]:
    session_response = await client.post(
        "/api/v1/agent/sessions",
        headers=headers,
        json={"title": "Stage 2 rehearsal"},
    )
    _assert_status(session_response, 201, "create session")
    session_id = session_response.json()["session"]["sessionId"]

    request_id = f"stage2-{uuid4().hex}"
    chat_payload = {
        "message": "请简要介绍这个 AI 导航站点。",
        "sessionId": session_id,
        "pageContext": {"page": "assistant", "url": "/assistant.html"},
    }
    stream_response = await client.post(
        "/api/v1/agent/chat/stream",
        headers={**headers, "X-Request-Id": request_id},
        json=chat_payload,
    )
    _assert_status(stream_response, 200, "stream chat")
    first_events = _parse_sse(stream_response.text)
    first_names = [event["event"] for event in first_events]
    completed = [
        event for event in first_events if event["event"] == "response.completed"
    ]
    if not completed:
        raise RuntimeError("Stream did not emit response.completed")
    first_response = completed[-1]["response"]

    retry_response = await client.post(
        "/api/v1/agent/chat/stream",
        headers={**headers, "X-Request-Id": request_id},
        json=chat_payload,
    )
    _assert_status(retry_response, 200, "manual retry")
    retry_events = _parse_sse(retry_response.text)
    retry_completed = [
        event for event in retry_events if event["event"] == "response.completed"
    ]
    if not retry_completed:
        raise RuntimeError("Manual retry did not emit response.completed")
    retried_response = retry_completed[-1]["response"]

    detail_response = await client.get(
        f"/api/v1/agent/sessions/{session_id}",
        headers=headers,
    )
    _assert_status(detail_response, 200, "session detail")
    detail = detail_response.json()
    messages = detail["messages"]

    delete_response = await client.delete(
        f"/api/v1/agent/sessions/{session_id}",
        headers=headers,
    )
    _assert_status(delete_response, 204, "delete session")

    checks = {
        "sessionCreated": session_id.startswith("ags_"),
        "streamStarted": bool(first_names)
        and first_names[0] == "response.started",
        "streamCompleted": first_names[-1] == "response.completed",
        "deterministicResponse": first_response["meta"]["mode"] == "deterministic",
        "requestIdStable": all(
            event["requestId"] == request_id
            for event in first_events + retry_events
        ),
        "manualRetryEquivalent": retried_response == first_response,
        "manualRetryDidNotDuplicateMessages": len(messages) == 2
        and detail["meta"]["totalCount"] == 2,
        "sessionRolesCorrect": [item["role"] for item in messages]
        == ["user", "assistant"],
        "sessionDeleted": delete_response.status_code == 204,
    }
    return {
        "checks": checks,
        "streamEventCount": len(first_events),
        "retryEventCount": len(retry_events),
        "sessionMessageCount": len(messages),
    }


async def _run_rollback_profile(
    client: Any,
    headers: dict[str, str],
) -> dict[str, Any]:
    stream_response = await client.post(
        "/api/v1/agent/chat/stream",
        headers={**headers, "X-Request-Id": f"rollback-{uuid4().hex}"},
        json={"message": "回滚验证", "pageContext": {}},
    )
    session_response = await client.post(
        "/api/v1/agent/sessions",
        headers=headers,
        json={"title": "must remain disabled"},
    )
    json_response = await client.post(
        "/api/v1/agent/chat",
        headers={**headers, "X-Request-Id": f"rollback-{uuid4().hex}"},
        json={"message": "回滚后的 JSON 验证", "pageContext": {}},
    )
    _assert_status(json_response, 200, "rollback JSON chat")
    return {
        "checks": {
            "streamRejected": stream_response.status_code == 503,
            "sessionsRejected": session_response.status_code == 503,
            "jsonChatAvailable": json_response.status_code == 200,
            "jsonChatDeterministic": (
                json_response.json()["meta"]["mode"] == "deterministic"
            ),
        },
        "streamStatus": stream_response.status_code,
        "sessionsStatus": session_response.status_code,
        "jsonStatus": json_response.status_code,
    }


async def _run_profile(profile: str, database_path: Path) -> dict[str, Any]:
    _configure_environment(database_path, profile)

    import httpx

    from app.db.database import get_connection, initialize_database
    from app.main import app

    initialize_database()
    with get_connection() as conn:
        migration_rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    migration_versions = [row["version"] for row in migration_rows]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
    ) as client:
        ready_response = await client.get("/api/v1/health/ready")
        _assert_status(ready_response, 200, "readiness")
        capabilities_response = await client.get(
            "/api/v1/agent/capabilities"
        )
        _assert_status(capabilities_response, 200, "capabilities")

        access_token = await _register_rehearsal_user(client, database_path)
        headers = {"Authorization": f"Bearer {access_token}"}
        runtime_response = await client.get(
            "/api/v1/agent/operations/runtime",
            headers=headers,
        )
        _assert_status(runtime_response, 200, "runtime snapshot")

        ready = ready_response.json()
        capabilities = capabilities_response.json()
        runtime = runtime_response.json()
        common_checks = {
            "ready": ready["status"] == "ready",
            "migration018Applied": (
                "018_agent_short_term_sessions.sql" in migration_versions
            ),
            "providerDeterministic": (
                runtime["provider"]["mode"] == "deterministic"
                and runtime["provider"]["live"] is False
            ),
            "defaultModelFlash": (
                runtime["provider"]["model"] == "qwen3.5-flash"
            ),
            "upgradeRatioZero": (
                runtime["provider"]["upgradeModel"] == "qwen3.7-plus"
                and runtime["provider"]["upgradeRatio"] == 0
            ),
            "runtimeSnapshotBounded": (
                runtime["meta"]["containsSecrets"] is False
                and runtime["meta"]["containsProviderEndpoint"] is False
                and _runtime_is_bounded(runtime)
            ),
            "singleWorker": (
                runtime["topology"]["declaredWorkers"] == 1
                and runtime["topology"]["stateBackend"] == "process_local"
            ),
        }
        if profile == "enabled":
            profile_result = await _run_enabled_profile(client, headers)
            common_checks["capabilitiesEnabled"] = (
                capabilities["stream"] is True
                and capabilities["sessions"] is True
            )
        else:
            profile_result = await _run_rollback_profile(client, headers)
            common_checks["capabilitiesDisabled"] = (
                capabilities["stream"] is False
                and capabilities["sessions"] is False
            )

    checks = {**common_checks, **profile_result["checks"]}
    return {
        "profile": profile,
        "passed": all(checks.values()),
        "checks": checks,
        "migrationCount": ready["migrationCount"],
        **{
            key: value
            for key, value in profile_result.items()
            if key != "checks"
        },
    }


def _run_child(profile: str, database_path: Path) -> dict[str, Any]:
    child_environment = os.environ.copy()
    child_environment["PYTHONPATH"] = str(
        Path(__file__).resolve().parents[1] / "backend"
    )
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--profile",
        profile,
        "--database",
        str(database_path),
    ]
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        env=child_environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    result_line = next(
        (
            line
            for line in reversed(completed.stdout.splitlines())
            if line.startswith(RESULT_PREFIX)
        ),
        None,
    )
    if result_line is None:
        diagnostic = completed.stderr.strip().splitlines()
        summary = diagnostic[-1] if diagnostic else "no diagnostic available"
        raise RuntimeError(
            f"{profile} rehearsal produced no result: {summary}"
        )
    result = json.loads(result_line[len(RESULT_PREFIX) :])
    if completed.returncode not in {0, 1}:
        raise RuntimeError(
            f"{profile} rehearsal exited unexpectedly with "
            f"{completed.returncode}"
        )
    return result


def _run_parent() -> int:
    with tempfile.TemporaryDirectory(prefix="ai-nav-agent-stage2-") as temp_dir:
        root = Path(temp_dir)
        profiles = [
            _run_child(profile, root / f"{profile}.sqlite3")
            for profile in PROFILES
        ]
    checks_passed = sum(
        1
        for profile in profiles
        for passed in profile["checks"].values()
        if passed
    )
    checks_total = sum(len(profile["checks"]) for profile in profiles)
    report = {
        "contractVersion": 1,
        "scenario": "agent-stage2-deterministic-release-rehearsal",
        "providerNetworkUsed": False,
        "realCredentialsLoaded": False,
        "passed": all(profile["passed"] for profile in profiles),
        "checksPassed": checks_passed,
        "checksTotal": checks_total,
        "profiles": profiles,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Agent Stage 2 release rehearsal."
    )
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    if args.profile:
        if args.database is None:
            parser.error("--database is required with --profile")
        result = asyncio.run(
            _run_profile(args.profile, args.database.resolve())
        )
        print(f"{RESULT_PREFIX}{json.dumps(result, ensure_ascii=False)}")
        return 0 if result["passed"] else 1
    if args.database is not None:
        parser.error("--database requires --profile")
    return _run_parent()


if __name__ == "__main__":
    raise SystemExit(main())
