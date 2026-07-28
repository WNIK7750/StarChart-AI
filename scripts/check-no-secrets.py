from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import NamedTuple, Sequence


MAX_FILE_BYTES = 1024 * 1024
DATABASE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
RELEASE_ASSET_SUFFIXES = {".ico", ".jpg", ".jpeg", ".png", ".webp"}
IGNORED_DIRECTORY_NAMES = {".git", ".venv", "__pycache__", "node_modules"}
TEST_PLACEHOLDERS = (
    "synthetic-test-only",
    "<set-at-deploy-time>",
    "<test-placeholder>",
)


class Finding(NamedTuple):
    path: Path
    line: int
    rule: str


LINE_RULES = (
    ("PRIVATE_KEY_HEADER", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("BEARER_TOKEN", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")),
    (
        "COOKIE_VALUE",
        re.compile(
            r"(?i)\b(?:Cookie|Set-Cookie)\s*:\s*"
            r"[A-Za-z0-9!#$%&'*+.^_`|~-]+=[^;\s\"']{4,}"
        ),
    ),
    (
        "PROVIDER_API_KEY",
        re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{20,}\b"),
    ),
)
SENSITIVE_ASSIGNMENT = re.compile(
    r"^\s*(?:export\s+)?"
    r"[A-Z_][A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|COOKIE)"
    r"\s*=\s*(?P<value>[^#\r\n]*?)\s*$",
)


def _is_env_example(path: Path) -> bool:
    return path.name.lower().endswith(".env.example")


def _is_sensitive_env_file(path: Path) -> bool:
    name = path.name.lower()
    return name == ".env" or (
        name.startswith(".env.") and not name.endswith(".env.example")
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _forbidden_path_finding(
    path: Path,
    *,
    allow_release_assets: bool = False,
) -> Finding | None:
    if _is_sensitive_env_file(path):
        return Finding(path, 0, "SENSITIVE_ENV_FILE")
    if path.suffix.lower() in DATABASE_SUFFIXES:
        return Finding(path, 0, "DATABASE_ARTIFACT")
    if "uploads" in {part.lower() for part in path.parts}:
        return Finding(path, 0, "UPLOAD_ARTIFACT")
    if path.is_symlink():
        return Finding(path, 0, "SYMLINK_ARTIFACT")
    try:
        size = path.stat().st_size
    except OSError:
        return Finding(path, 0, "UNREADABLE_FILE")
    if size > MAX_FILE_BYTES and not (
        allow_release_assets and path.suffix.lower() in RELEASE_ASSET_SUFFIXES
    ):
        return Finding(path, 0, "OVERSIZED_FILE")
    return None


def _scan_file(
    path: Path,
    *,
    allow_release_assets: bool = False,
) -> list[Finding]:
    forbidden = _forbidden_path_finding(
        path,
        allow_release_assets=allow_release_assets,
    )
    if forbidden is not None:
        return [forbidden]
    try:
        with path.open("rb") as stream:
            prefix = stream.read(4096)
    except OSError:
        return [Finding(path, 0, "UNREADABLE_FILE")]
    if b"\x00" in prefix:
        if allow_release_assets and path.suffix.lower() in RELEASE_ASSET_SUFFIXES:
            return []
        return [Finding(path, 0, "BINARY_ARTIFACT")]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        if allow_release_assets and path.suffix.lower() in RELEASE_ASSET_SUFFIXES:
            return []
        return [Finding(path, 0, "BINARY_ARTIFACT")]

    findings: list[Finding] = []
    is_example = _is_env_example(path)
    for number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in LINE_RULES:
            if pattern.search(line):
                findings.append(Finding(path, number, rule))
        assignment = SENSITIVE_ASSIGNMENT.match(line)
        if assignment is not None:
            value = assignment.group("value").strip().strip("\"'")
            if not value:
                continue
            if is_example and any(marker in value.lower() for marker in TEST_PLACEHOLDERS):
                continue
            findings.append(Finding(path, number, "SENSITIVE_ASSIGNMENT"))
    return findings


def _iter_files(path: Path) -> list[Path]:
    if path.is_file() or path.is_symlink():
        return [path]
    files: list[Path] = []
    for current, directory_names, file_names in os.walk(path, followlinks=False):
        current_path = Path(current)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in IGNORED_DIRECTORY_NAMES
        )
        for name in sorted(file_names):
            files.append(current_path / name)
    return files


def scan_paths(
    paths: Sequence[Path],
    *,
    allowed_root: Path,
    allow_release_assets: bool = False,
) -> list[Finding]:
    root = allowed_root.resolve()
    findings: list[Finding] = []
    seen: set[Path] = set()
    for requested in paths:
        candidate = requested.resolve()
        if not _is_within(candidate, root):
            findings.append(Finding(candidate, 0, "OUTSIDE_SCAN_ROOT"))
            continue
        if not candidate.exists():
            findings.append(Finding(candidate, 0, "MISSING_PATH"))
            continue
        if candidate.is_dir() and candidate.name.lower() == "uploads":
            findings.append(Finding(candidate, 0, "UPLOAD_ARTIFACT"))
            continue
        for path in _iter_files(candidate):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            findings.extend(
                _scan_file(path, allow_release_assets=allow_release_assets)
            )
    return findings


def format_finding(finding: Finding, root: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = finding.path.resolve()
    try:
        display = resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        display = resolved_path.name
    return f"{display}:{finding.line}:{finding.rule}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan scoped project paths without echoing matched values."
    )
    path_source = parser.add_mutually_exclusive_group(required=True)
    path_source.add_argument("--paths", nargs="+", type=Path)
    path_source.add_argument(
        "--paths-file",
        type=Path,
        help="UTF-8 file containing one scoped path per line.",
    )
    parser.add_argument(
        "--allow-release-assets",
        action="store_true",
        help="Allow only known image asset suffixes to be binary or oversized.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd().resolve()
    paths = args.paths
    if args.paths_file is not None:
        try:
            paths = [
                Path(line)
                for line in args.paths_file.read_text(encoding="utf-8").splitlines()
                if line
            ]
        except (OSError, UnicodeDecodeError):
            print("PATH_LIST_UNREADABLE")
            return 1
    findings = scan_paths(
        paths,
        allowed_root=root,
        allow_release_assets=args.allow_release_assets,
    )
    for finding in findings:
        print(format_finding(finding, root))
    if findings:
        print(f"NO_SECRETS_CHECK_FAILED: {len(findings)} finding(s)")
        return 1
    print("No secret-shaped values or forbidden artifacts found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
