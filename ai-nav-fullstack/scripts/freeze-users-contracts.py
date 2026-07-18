import json
import sqlite3
import tempfile
from pathlib import Path

from fastapi import FastAPI

from app.api.v1.routers import agent, assets, auth, common, operations, privacy, user_learning, users
from app.core.security import hash_password, hash_token
from app.db.database import apply_migrations, dict_factory
from app.users.authentication.repositories.sqlite import SQLiteAuthenticationRepository
from app.users.authentication.service import AuthenticationService, RequestContext
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


def connection_factory(database_path: Path):
    def connect():
        conn = sqlite3.connect(database_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    return connect


def seed_database(database_path: Path) -> int:
    conn = sqlite3.connect(database_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
        apply_migrations(conn, ROOT / "database" / "migrations")
        conn.execute(
            "INSERT INTO user_accounts(user_uid, username, email, account_status) VALUES ('usr_contract', 'contract_user', 'contract@example.test', 'active')"
        )
        user_id = conn.execute("SELECT id FROM user_accounts WHERE user_uid = 'usr_contract'").fetchone()[0]
        conn.execute(
            "INSERT INTO user_auth_passwords(user_id, password_hash) VALUES (?, ?)",
            (user_id, hash_password("Current123")),
        )
        conn.execute("INSERT INTO user_profiles(user_id, display_name) VALUES (?, 'Contract User')", (user_id,))
        conn.execute("INSERT INTO user_preferences(user_id) VALUES (?)", (user_id,))
        conn.execute(
            """
            INSERT INTO user_privacy_consent_events(
                event_uid, user_id, consent_type, policy_version, action, source
            ) VALUES ('cons_contract', ?, 'privacy_policy', '2026-07-01', 'granted', 'registration')
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
            VALUES ('sess_contract', ?, ?, 'contract browser', datetime('now', '+1 day'))
            """,
            (user_id, hash_token("contract-refresh-token")),
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def auth_users_openapi() -> dict:
    app = FastAPI(title="Auth Users Contract Baseline")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(common.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(assets.router, prefix="/api/v1")
    app.include_router(agent.router, prefix="/api/v1")
    app.include_router(operations.router, prefix="/api/v1")
    app.include_router(privacy.router, prefix="/api/v1")
    app.include_router(user_learning.router, prefix="/api/v1")
    schema = app.openapi()
    paths = {
        path: methods
        for path, methods in sorted(schema["paths"].items())
        if path.startswith("/api/v1/auth")
        or path.startswith("/api/v1/users")
        or path.startswith("/api/v1/health")
        or path == "/api/v1/agent/workflows/save"
    }
    components = {
        key: value
        for key, value in sorted(schema.get("components", {}).get("schemas", {}).items())
        if any(
            name in key
            for name in (
                "Register",
                "Login",
                "Refresh",
                "Password",
                "Account",
                "Profile",
                "Preferences",
                "Security",
                "Workflow",
                "Privacy",
                "Consent",
                "Deletion",
                "Learning",
            )
        )
    }
    return {"openapi": schema["openapi"], "info": schema["info"], "paths": paths, "components": {"schemas": components}}


def response_samples(database_path: Path, user_id: int) -> dict:
    connect = connection_factory(database_path)
    audit = AuditService(SQLiteAuditRepository(connect))
    privacy = PrivacyService(SQLitePrivacyRepository(connect))
    services = {
        "auth": AuthenticationService(SQLiteAuthenticationRepository(connect), audit, privacy),
        "profile": ProfileService(SQLiteProfileRepository(connect)),
        "preferences": PreferencesService(SQLitePreferencesRepository(connect)),
        "sessions": SessionsService(SQLiteSessionsRepository(connect)),
    }
    context = RequestContext(ip_address="127.0.0.1", user_agent="contract-freeze")
    login = services["auth"].login({"identifier": "contract_user", "password": "Current123", "deviceName": "contract", "privacyAccepted": True}, context)
    refresh = services["auth"].refresh(login["refreshToken"], context)
    return {
        "auth.login": sorted(login),
        "auth.login.user": sorted(login["user"]),
        "auth.refresh": sorted(refresh),
        "auth.me": ["user"],
        "auth.me.user": sorted(auth._public_user(services["auth"].current_user_from_token(login["accessToken"]))),
        "users.profile.get": sorted(services["profile"].get_profile(user_id)),
        "users.profile.item": sorted(services["profile"].get_profile(user_id)["profile"]),
        "users.preferences.get": sorted(services["preferences"].get_preferences(user_id)),
        "users.preferences.item": sorted(services["preferences"].get_preferences(user_id)["preferences"]),
        "users.sessions.list": sorted(services["sessions"].list_sessions(user_id)),
        "users.sessions.meta": sorted(services["sessions"].list_sessions(user_id)["meta"]),
        "users.sessions.item": sorted(services["sessions"].list_sessions(user_id)["items"][0]),
    }


def main() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    (BASELINE_DIR / "auth_users_openapi.json").write_text(
        json.dumps(auth_users_openapi(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with tempfile.TemporaryDirectory() as temp:
        database_path = Path(temp) / "contract.sqlite3"
        user_id = seed_database(database_path)
        samples = response_samples(database_path, user_id)
    (BASELINE_DIR / "auth_users_response_shapes.json").write_text(
        json.dumps(samples, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote auth/users contract baselines to {BASELINE_DIR}")


if __name__ == "__main__":
    main()
