from app.main import iter_app_routes
from app.users.audit.events import AUDIT_EVENTS
from app.users.command_safety import COMMAND_SAFETY


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
LEARNING_AUDIT_EVENTS = {
    "learning.section_progress.updated",
    "learning.progress.updated",
    "learning.activity.recorded",
    "learning.favorite.added",
    "learning.favorite.removed",
}


def users_command_routes() -> set[tuple[str, str]]:
    commands: set[tuple[str, str]] = set()
    for route in iter_app_routes():
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        owned = path.startswith("/api/v1/users/") or path.startswith("/api/v1/auth/")
        owned = owned or path == "/api/v1/agent/workflows/save"
        if owned:
            commands.update((method, path) for method in methods & WRITE_METHODS)
    return commands


def main() -> None:
    actual = users_command_routes()
    registered = set(COMMAND_SAFETY)
    missing = sorted(actual - registered)
    stale = sorted(registered - actual)
    invalid_audits = sorted(
        (method, path, spec.audit)
        for (method, path), spec in COMMAND_SAFETY.items()
        for event in spec.audit.split("+")
        if event != "login-log" and event not in AUDIT_EVENTS and event not in LEARNING_AUDIT_EVENTS
    )
    incomplete = sorted(
        (method, path)
        for (method, path), spec in COMMAND_SAFETY.items()
        if not all((spec.domain, spec.audit, spec.replay, spec.concurrency))
    )
    if missing or stale or invalid_audits or incomplete:
        raise SystemExit(
            "Users command safety registry failed: "
            f"missing={missing}, stale={stale}, invalidAudits={invalid_audits}, incomplete={incomplete}"
        )
    print(f"Users command safety registry passed: {len(actual)} commands covered")


if __name__ == "__main__":
    main()
