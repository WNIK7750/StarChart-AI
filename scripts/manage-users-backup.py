import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def verify_database(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    conn = sqlite3.connect(path)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        migrations = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    finally:
        conn.close()
    if integrity != "ok" or foreign_key_errors:
        raise RuntimeError(f"Database verification failed: integrity={integrity}, foreignKeys={len(foreign_key_errors)}")
    return {"integrity": integrity, "foreignKeyErrors": 0, "migrationCount": migrations}


def backup_database(source: Path, output: Path) -> dict:
    if source.resolve() == output.resolve():
        raise ValueError("Backup output must differ from source")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        source_conn = sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True)
        output_conn = sqlite3.connect(temporary)
        try:
            source_conn.backup(output_conn)
        finally:
            output_conn.close()
            source_conn.close()
        verification = verify_database(temporary)
        os.replace(temporary, output)
        return verification
    finally:
        temporary.unlink(missing_ok=True)


def restore_database(backup: Path, target: Path, replace: bool = False) -> dict:
    verify_database(backup)
    if target.exists() and not replace:
        raise FileExistsError(f"Target exists; pass --replace to preserve it and restore: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    rollback_copy = None
    if target.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rollback_copy = target.with_name(f"{target.stem}.pre-restore-{timestamp}{target.suffix}")
        backup_database(target, rollback_copy)
    temporary = target.with_suffix(target.suffix + ".restore-tmp")
    temporary.unlink(missing_ok=True)
    try:
        backup_database(backup, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {**verify_database(target), "preRestoreBackup": str(rollback_copy) if rollback_copy else None}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create, verify, or restore a validated SQLite Users database backup.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--source", type=Path, required=True)
    backup_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--database", type=Path, required=True)
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--backup", type=Path, required=True)
    restore_parser.add_argument("--target", type=Path, required=True)
    restore_parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.command == "backup":
        result = backup_database(args.source, args.output)
    elif args.command == "verify":
        result = verify_database(args.database)
    else:
        result = restore_database(args.backup, args.target, args.replace)
    print(result)


if __name__ == "__main__":
    main()
