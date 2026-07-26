#!/usr/bin/env python3
"""Interactively create the sole account in an isolated HTTP test database."""

from __future__ import annotations

import getpass
import hashlib
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
# This one-shot tool must never inspect a developer's dotenv file.
os.environ["AI_NAV_DISABLE_DOTENV"] = "1"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import (  # noqa: E402
    APP_ENV,
    DATABASE_PATH,
    HTTP_TEST_ACCOUNT_USERNAME,
    MIGRATIONS_DIR,
    SCHEMA_PATH,
    SEED_PATH,
    UPLOAD_DIR,
)
from app.db.database import apply_migrations, dict_factory  # noqa: E402
from app.users.account.service import normalize_username  # noqa: E402
from app.users.audit.repositories.sqlite import SQLiteAuditRepository  # noqa: E402
from app.users.audit.service import AuditService  # noqa: E402
from app.users.authentication.repositories.sqlite import (  # noqa: E402
    SQLiteAuthenticationRepository,
)
from app.users.authentication.service import (  # noqa: E402
    AuthenticationService,
    RequestContext,
)
from app.users.privacy.repositories.sqlite import SQLitePrivacyRepository  # noqa: E402
from app.users.privacy.service import PrivacyService  # noqa: E402


ALLOWED_PROFILES = frozenset({"http_test", "provider_preview"})
PASSWORD_ENV_NAMES = frozenset(
    {
        "AI_NAV_HTTP_TEST_ACCOUNT_PASSWORD",
        "HTTP_TEST_ACCOUNT_PASSWORD",
    }
)


class ProvisioningError(RuntimeError):
    """A secret-safe account provisioning failure."""


def _is_inside_source_tree(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    return resolved == ROOT or ROOT in resolved.parents


def _validated_paths(database_path: Path, upload_dir: Path) -> tuple[Path, Path]:
    database = Path(database_path).expanduser().resolve()
    uploads = Path(upload_dir).expanduser().resolve()
    if _is_inside_source_tree(database) or _is_inside_source_tree(uploads):
        raise ProvisioningError("Provisioning paths must be external")
    if database.exists() and not database.is_file():
        raise ProvisioningError("Database target is invalid")
    if uploads.exists() and not uploads.is_dir():
        raise ProvisioningError("Upload target is invalid")
    return database, uploads


def _connection_factory(database_path: Path):
    def connect() -> sqlite3.Connection:
        conn = sqlite3.connect(database_path, timeout=5.0)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    return connect


def _prepare_staging_database(staging_path: Path, database_path: Path) -> None:
    if database_path.exists():
        with (
            closing(sqlite3.connect(database_path)) as source,
            closing(sqlite3.connect(staging_path)) as destination,
        ):
            source.backup(destination)

    with closing(sqlite3.connect(staging_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("PRAGMA busy_timeout = 5000")
        if not database_path.exists():
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
        apply_migrations(conn, MIGRATIONS_DIR)
        account_count = conn.execute("SELECT COUNT(*) FROM user_accounts").fetchone()[0]
        if account_count:
            raise ProvisioningError("Provisioning requires an empty account database")


def _build_authentication_service(database_path: Path) -> AuthenticationService:
    connection_factory = _connection_factory(database_path)
    return AuthenticationService(
        SQLiteAuthenticationRepository(connection_factory),
        audit=AuditService(SQLiteAuditRepository(connection_factory)),
        privacy=PrivacyService(SQLitePrivacyRepository(connection_factory)),
    )


def provision_http_test_account(
    username: str,
    password: str,
    *,
    database_path: Path,
    upload_dir: Path,
) -> dict[str, str]:
    """Create the only test account without returning credentials or tokens."""
    if APP_ENV not in ALLOWED_PROFILES:
        raise ProvisioningError("Provisioning is disabled for this deployment profile")

    try:
        allowed_username = normalize_username(HTTP_TEST_ACCOUNT_USERNAME)
        requested_username = normalize_username(username)
    except Exception:
        raise ProvisioningError("Account identifier is invalid") from None
    if requested_username != allowed_username:
        raise ProvisioningError("Account identifier is not permitted")

    database, uploads = _validated_paths(database_path, upload_dir)
    database.parent.mkdir(parents=True, exist_ok=True)
    staging_handle = tempfile.NamedTemporaryFile(
        prefix=".http-test-account-",
        suffix=".sqlite3",
        dir=database.parent,
        delete=False,
    )
    staging_path = Path(staging_handle.name)
    staging_handle.close()
    upload_created = False

    try:
        _prepare_staging_database(staging_path, database)
        authentication = _build_authentication_service(staging_path)
        context = RequestContext(ip_address="127.0.0.1", user_agent="account-provisioner")
        registration = authentication.register(
            {
                "username": requested_username,
                "password": password,
                "displayName": "HTTP Test User",
                "email": None,
                "phone": None,
                "privacyAccepted": True,
            },
            context,
        )
        user_uid = registration["user"]["userUid"]
        with closing(_connection_factory(staging_path)()) as conn:
            user_id = conn.execute(
                "SELECT id FROM user_accounts WHERE user_uid = ?",
                (user_uid,),
            ).fetchone()["id"]
        authentication.logout(user_id, registration["refreshToken"])
        registration.clear()

        with closing(_connection_factory(staging_path)()) as conn:
            account_count = conn.execute(
                "SELECT COUNT(*) AS count FROM user_accounts"
            ).fetchone()["count"]
            active_sessions = conn.execute(
                "SELECT COUNT(*) AS count FROM user_sessions WHERE is_revoked = 0"
            ).fetchone()["count"]
        if account_count != 1 or active_sessions:
            raise ProvisioningError("Provisioning verification failed")

        if not uploads.exists():
            uploads.mkdir(parents=True, exist_ok=False)
            upload_created = True
        os.replace(staging_path, database)
        return {
            "status": "created",
            "userDigest": hashlib.sha256(user_uid.encode("utf-8")).hexdigest()[:12],
            "externalPaths": "validated",
        }
    except ProvisioningError:
        if upload_created and uploads.exists():
            uploads.rmdir()
        raise
    except Exception as exc:
        if upload_created and uploads.exists():
            uploads.rmdir()
        raise ProvisioningError(
            f"Account provisioning failed ({type(exc).__name__})"
        ) from None
    finally:
        if staging_path.exists():
            staging_path.unlink()


def main(
    argv: list[str] | None = None,
    *,
    stdin=None,
    input_fn=input,
    password_fn=getpass.getpass,
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stdin = sys.stdin if stdin is None else stdin
    if argv:
        print("Provisioning accepts no command-line arguments.", file=sys.stderr)
        return 2
    if any(os.getenv(name) for name in PASSWORD_ENV_NAMES):
        print("Password environment input is not permitted.", file=sys.stderr)
        return 2
    if not stdin.isatty():
        print("Provisioning requires an interactive terminal.", file=sys.stderr)
        return 2

    try:
        username = input_fn("Username: ")
        password = password_fn("Password: ")
        result = provision_http_test_account(
            username,
            password,
            database_path=DATABASE_PATH,
            upload_dir=UPLOAD_DIR,
        )
    except (EOFError, KeyboardInterrupt, ProvisioningError):
        print("Provisioning did not complete.", file=sys.stderr)
        return 1
    finally:
        if "password" in locals():
            password = ""

    print(
        f"Account provisioning {result['status']}; "
        f"user digest {result['userDigest']}; "
        f"external paths {result['externalPaths']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
