import json
import sqlite3
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.security import hash_password, hash_token
from app.db.database import apply_migrations, dict_factory
from app.users.authentication.repositories.sqlite import SQLiteAuthenticationRepository
from app.users.authentication.service import AuthenticationService, RequestContext
from app.users.authentication.rate_limit import SQLiteAuthRateLimitRepository
from app.users.assets.repositories.sqlite import SQLiteAssetsRepository
from app.users.audit.repositories.sqlite import SQLiteAuditRepository
from app.users.audit.service import AuditService
from app.users.preferences.repositories.sqlite import SQLitePreferencesRepository
from app.users.preferences.service import PreferencesService
from app.users.privacy.repositories.sqlite import SQLitePrivacyRepository
from app.users.privacy.service import PrivacyService
from app.users.profile.repositories.sqlite import SQLiteProfileRepository
from app.users.profile.service import ProfileService
from app.users.sessions.repositories.sqlite import SQLiteSessionsRepository
from app.users.sessions.service import SessionsService


ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "docs" / "users-baseline"
BUDGETS = {
    "auth.login": {"p95Ms": 250.0, "maxStatements": 8},
    "auth.current_user_from_token": {"p95Ms": 10.0, "maxStatements": 1},
    "auth.refresh_rotate": {"p95Ms": 25.0, "maxStatements": 5},
    "auth.rate_limit.consume": {"p95Ms": 15.0, "maxStatements": 3},
    "users.profile.get": {"p95Ms": 10.0, "maxStatements": 1},
    "users.preferences.get": {"p95Ms": 10.0, "maxStatements": 1},
    "users.sessions.list": {"p95Ms": 15.0, "maxStatements": 2},
    "users.assets.workflows.list": {"p95Ms": 15.0, "maxStatements": 2},
}


@dataclass
class QueryCounter:
    count: int = 0


def connect_factory(database_path: str, counter: QueryCounter | None = None):
    def connect():
        conn = sqlite3.connect(database_path, uri=True, timeout=5.0)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        if counter is not None:
            def trace(statement: str) -> None:
                first = statement.strip().split(None, 1)[0].upper() if statement.strip() else ""
                if first in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
                    counter.count += 1

            conn.set_trace_callback(trace)
        return conn

    return connect


def seed(database_path: str) -> tuple[int, sqlite3.Connection]:
    conn = sqlite3.connect(database_path, uri=True)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
        apply_migrations(conn, ROOT / "database" / "migrations")
        conn.execute(
            "INSERT INTO user_accounts(user_uid, username, email, account_status) VALUES ('usr_bench', 'bench_user', 'bench@example.test', 'active')"
        )
        user_id = conn.execute("SELECT id FROM user_accounts WHERE user_uid = 'usr_bench'").fetchone()[0]
        conn.execute("INSERT INTO user_auth_passwords(user_id, password_hash) VALUES (?, ?)", (user_id, hash_password("Current123")))
        conn.execute("INSERT INTO user_profiles(user_id, display_name) VALUES (?, 'Bench User')", (user_id,))
        conn.execute("INSERT INTO user_preferences(user_id) VALUES (?)", (user_id,))
        conn.execute(
            """
            INSERT INTO user_privacy_consent_events(
                event_uid, user_id, consent_type, policy_version, action, source
            ) VALUES ('cons_bench', ?, 'privacy_policy', '2026-07-01', 'granted', 'registration')
            """,
            (user_id,),
        )
        conn.execute(
            "INSERT INTO user_role_assignments(user_id, role_id) SELECT ?, id FROM roles WHERE code = 'user'",
            (user_id,),
        )
        conn.execute(
            """
            INSERT INTO user_sessions(session_uid, user_id, refresh_token_hash, device_name, expires_at)
            VALUES ('sess_bench', ?, ?, 'bench browser', datetime('now', '+1 day'))
            """,
            (user_id, hash_token("bench-refresh-token")),
        )
        conn.commit()
        return user_id, conn
    except Exception:
        conn.close()
        raise


def measure(name: str, fn, sample_count: int, counter: QueryCounter) -> dict:
    timings = []
    query_counts = []
    for _ in range(sample_count):
        counter.count = 0
        started = time.perf_counter()
        fn()
        timings.append((time.perf_counter() - started) * 1000)
        query_counts.append(counter.count)
    timings.sort()
    query_counts.sort()
    return {
        "operation": name,
        "sampleCount": sample_count,
        "p50Ms": round(statistics.median(timings), 3),
        "p95Ms": round(timings[int(sample_count * 0.95) - 1], 3),
        "maxMs": round(max(timings), 3),
        "p50Statements": round(statistics.median(query_counts), 1),
        "maxStatements": max(query_counts),
    }


def query_plan_checks(database_path: str) -> list[dict]:
    queries = {
        "users.sessions.list": (
            "SELECT * FROM user_sessions WHERE user_id = ? ORDER BY is_revoked, last_seen_at DESC, created_at DESC LIMIT ? OFFSET ?",
            (1, 20, 0),
            "idx_user_sessions_user",
        ),
        "users.assets.workflows.list": (
            "SELECT * FROM user_saved_workflows WHERE user_id = ? AND status = ? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?",
            (1, "active", 20, 0),
            "idx_user_saved_workflows_list",
        ),
        "auth.rate_limit.expiry": (
            "SELECT scope FROM user_auth_rate_limits WHERE expires_at < ?",
            (1_800_000_000,),
            "idx_user_auth_rate_limits_expiry",
        ),
    }
    checks = []
    conn = sqlite3.connect(database_path, uri=True)
    try:
        for operation, (query, params, expected_index) in queries.items():
            details = [row[3] for row in conn.execute(f"EXPLAIN QUERY PLAN {query}", params).fetchall()]
            passed = any(expected_index in detail for detail in details)
            checks.append({
                "operation": operation,
                "expectedIndex": expected_index,
                "plan": details,
                "passed": passed,
            })
    finally:
        conn.close()
    return checks


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        # Shared-memory SQLite keeps this a service/query microbenchmark instead
        # of measuring host filesystem and antivirus latency.
        database_path = f"file:users-benchmark-{Path(temp).name}?mode=memory&cache=shared"
        user_id, anchor_connection = seed(database_path)
        counter = QueryCounter()
        factory = connect_factory(database_path, counter)
        audit = AuditService(SQLiteAuditRepository(factory))
        privacy = PrivacyService(SQLitePrivacyRepository(factory))
        auth = AuthenticationService(SQLiteAuthenticationRepository(factory), audit, privacy)
        profile = ProfileService(SQLiteProfileRepository(factory))
        preferences = PreferencesService(SQLitePreferencesRepository(factory))
        sessions = SessionsService(SQLiteSessionsRepository(factory))
        assets = SQLiteAssetsRepository(factory)
        rate_limits = SQLiteAuthRateLimitRepository(factory)
        context = RequestContext(ip_address="127.0.0.1", user_agent="users-benchmark")
        login = auth.login({"identifier": "bench_user", "password": "Current123", "deviceName": "benchmark", "privacyAccepted": True}, context)
        assets.create_workflow(
            user_id,
            "workflow_bench",
            "workflow-benchmark",
            {"title": "Benchmark", "description": None, "sourceType": "manual", "sourceRef": None},
            [{"stepUid": "step_bench", "order": 1, "name": "Benchmark", "objective": "Measure", "toolSlug": None}],
        )
        current_refresh = {"token": login["refreshToken"]}

        def refresh_once():
            refreshed = auth.refresh(current_refresh["token"], context)
            current_refresh["token"] = refreshed["refreshToken"]
            return refreshed

        sample_count = 50
        results = [
            measure(
                "auth.login",
                lambda: auth.login({"identifier": "bench_user", "password": "Current123", "deviceName": "benchmark", "privacyAccepted": True}, context),
                10,
                counter,
            ),
            measure("auth.current_user_from_token", lambda: auth.current_user_from_token(login["accessToken"]), sample_count, counter),
            measure("auth.refresh_rotate", refresh_once, sample_count, counter),
            measure(
                "auth.rate_limit.consume",
                lambda: rate_limits.consume("benchmark:ip", "a" * 64, 1000, 60, 1_800_000_000),
                sample_count,
                counter,
            ),
            measure("users.profile.get", lambda: profile.get_profile(user_id), sample_count, counter),
            measure("users.preferences.get", lambda: preferences.get_preferences(user_id), sample_count, counter),
            measure("users.sessions.list", lambda: sessions.list_sessions(user_id, page=1, page_size=20), sample_count, counter),
            measure("users.assets.workflows.list", lambda: assets.list_workflows(user_id, "active", 20, 0), sample_count, counter),
        ]
        plans = query_plan_checks(database_path)
        for result in results:
            budget = BUDGETS[result["operation"]]
            result["budget"] = budget
            result["withinBudget"] = (
                result["p95Ms"] <= budget["p95Ms"]
                and result["maxStatements"] <= budget["maxStatements"]
            )
        passed = all(result["withinBudget"] for result in results) and all(check["passed"] for check in plans)
        anchor_connection.close()
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    output = BASELINE_DIR / "users_performance_baseline.json"
    report = {"passed": passed, "operations": results, "queryPlans": plans}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    print(f"Wrote users performance baseline to {output}")
    if not passed:
        raise SystemExit("Users performance budget failed")


if __name__ == "__main__":
    main()
