import hashlib
import importlib.util
import json
import sqlite3
import tempfile
from pathlib import Path

from app.db.database import apply_migrations


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "users-baseline" / "users_release_rehearsal.json"
BACKUP_SCRIPT = Path(__file__).with_name("manage-users-backup.py")
BACKUP_SPEC = importlib.util.spec_from_file_location("manage_users_backup", BACKUP_SCRIPT)
if BACKUP_SPEC is None or BACKUP_SPEC.loader is None:
    raise RuntimeError(f"Cannot load backup helpers from {BACKUP_SCRIPT}")
BACKUP_MODULE = importlib.util.module_from_spec(BACKUP_SPEC)
BACKUP_SPEC.loader.exec_module(BACKUP_MODULE)
backup_database = BACKUP_MODULE.backup_database
restore_database = BACKUP_MODULE.restore_database
verify_database = BACKUP_MODULE.verify_database


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        source = temp_dir / "source.sqlite3"
        backup = temp_dir / "backup.sqlite3"
        restored = temp_dir / "restored.sqlite3"
        conn = sqlite3.connect(source)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
            conn.executescript((ROOT / "database" / "seed.sql").read_text(encoding="utf-8"))
            apply_migrations(conn, ROOT / "database" / "migrations")
            conn.execute(
                "INSERT INTO user_accounts(user_uid, username, email, account_status) VALUES (?, ?, ?, 'active')",
                ("usr_release_canary", "release_canary", "release-canary@example.test"),
            )
            conn.commit()
        finally:
            conn.close()
        source_check = verify_database(source)
        backup_check = backup_database(source, backup)
        restore_check = restore_database(backup, restored)
        conn = sqlite3.connect(restored)
        try:
            canary_count = conn.execute(
                "SELECT COUNT(*) FROM user_accounts WHERE user_uid = 'usr_release_canary'"
            ).fetchone()[0]
            migrations = dict(conn.execute("SELECT version, checksum FROM schema_migrations").fetchall())
        finally:
            conn.close()
        expected = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "database" / "migrations").glob("*.sql"))
        }
        checksum_match = migrations == expected
        passed = canary_count == 1 and checksum_match
        report = {
            "passed": passed,
            "source": source_check,
            "backup": backup_check,
            "restore": restore_check,
            "canaryRestored": canary_count == 1,
            "migrationChecksumsMatch": checksum_match,
            "migrationCount": len(migrations),
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        if not passed:
            raise SystemExit("Users release rehearsal failed")


if __name__ == "__main__":
    main()
