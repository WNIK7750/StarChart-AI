import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import Request

from app.core.config import API_PREFIX
from app.users.observability.metrics import get_users_metrics


LOGGER = logging.getLogger("app.users.access")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
OBSERVED_PREFIXES = (f"{API_PREFIX}/auth", f"{API_PREFIX}/users")
OPERATION_NAMES = {
    ("POST", f"{API_PREFIX}/auth/register"): "auth.register",
    ("POST", f"{API_PREFIX}/auth/login"): "auth.login",
    ("POST", f"{API_PREFIX}/auth/refresh"): "auth.refresh",
    ("PATCH", f"{API_PREFIX}/users/me/password"): "users.password.update",
    ("DELETE", f"{API_PREFIX}/users/me/sessions/{{session_uid}}"): "users.session.revoke",
    ("POST", f"{API_PREFIX}/users/me/sessions/revoke-others"): "users.sessions.revoke_others",
    ("POST", f"{API_PREFIX}/agent/workflows/save"): "users.assets.agent_save",
}


def is_observed_request(path: str) -> bool:
    return path.startswith(OBSERVED_PREFIXES) or path == f"{API_PREFIX}/agent/workflows/save"


def request_id(value: str | None) -> str:
    return value if value and REQUEST_ID_PATTERN.fullmatch(value) else uuid4().hex


def operation_name(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None) or request.url.path
    return OPERATION_NAMES.get((request.method, route_path), f"{request.method} {route_path}")


async def observe_users_request(request: Request, call_next):
    if not is_observed_request(request.url.path):
        return await call_next(request)
    trace_id = request_id(request.headers.get("X-Request-Id"))
    request.state.request_id = trace_id
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((perf_counter() - started) * 1000, 2)
        operation = operation_name(request)
        get_users_metrics().record(operation, 500, "UNHANDLED_EXCEPTION")
        LOGGER.exception(json.dumps({
            "requestId": trace_id,
            "operation": operation,
            "status": 500,
            "latencyMs": latency_ms,
            "errorCode": "UNHANDLED_EXCEPTION",
        }, ensure_ascii=True))
        raise
    latency_ms = round((perf_counter() - started) * 1000, 2)
    operation = operation_name(request)
    error_code = getattr(request.state, "error_code", None)
    if response.status_code >= 400 and not error_code:
        error_code = f"HTTP_{response.status_code}"
    get_users_metrics().record(operation, response.status_code, error_code)
    response.headers["X-Request-Id"] = trace_id
    response.headers["Server-Timing"] = f"users;dur={latency_ms}"
    LOGGER.info(json.dumps({
        "requestId": trace_id,
        "operation": operation,
        "status": response.status_code,
        "latencyMs": latency_ms,
        "errorCode": error_code,
    }, ensure_ascii=True))
    return response
