import json
import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers import agent, assets, auth, common, learning, operations, privacy, tools, user_learning, users
from app.core.config import (
    API_PREFIX,
    APP_NAME,
    APP_ENV,
    AVATAR_MAX_REQUEST_BYTES,
    CORS_ALLOW_ORIGINS,
    FRONTEND_DIR,
    HTTPS_CONFIRMED,
    UPLOAD_DIR,
)
from app.db.database import initialize_database
from app.users.observability.access import observe_users_request


UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
learning_logger = logging.getLogger("app.learning.access")


def iter_app_routes():
    """Yield concrete routes across FastAPI's eager and lazy router representations."""
    for route in app.routes:
        effective_candidates = getattr(route, "effective_candidates", None)
        if callable(effective_candidates):
            yield from effective_candidates()
        else:
            yield route


app.middleware("http")(observe_users_request)


async def security_response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()"
    )
    if APP_ENV == "production" and HTTPS_CONFIRMED:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def bound_avatar_multipart_request(request: Request, call_next):
    if request.method == "POST" and request.url.path == f"{API_PREFIX}/users/me/avatar":
        raw_length = request.headers.get("content-length")
        if raw_length is None:
            return JSONResponse(
                status_code=411,
                content={"detail": {"code": "CONTENT_LENGTH_REQUIRED", "message": "Content-Length is required"}},
            )
        try:
            content_length = int(raw_length)
        except ValueError:
            content_length = -1
        if content_length < 0 or content_length > AVATAR_MAX_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": {"code": "AVATAR_REQUEST_TOO_LARGE", "message": "Avatar request exceeds limit"}},
            )
    return await call_next(request)


@app.middleware("http")
async def learning_access_log(request: Request, call_next):
    is_learning_request = request.url.path.startswith(f"{API_PREFIX}/learning") or request.url.path.startswith(
        f"{API_PREFIX}/users/me/learning"
    )
    if not is_learning_request:
        return await call_next(request)

    request_id = request.headers.get("X-Request-Id") or uuid4().hex
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency_ms = round((perf_counter() - started) * 1000, 2)
        learning_logger.exception(json.dumps({
            "requestId": request_id,
            "operation": f"{request.method} {request.url.path}",
            "statusCode": 500,
            "latencyMs": latency_ms,
            "errorCode": "UNHANDLED_EXCEPTION",
            "viewerType": "authenticated" if request.headers.get("Authorization") else "anonymous",
        }, ensure_ascii=False))
        raise
    latency_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-Id"] = request_id
    response.headers["Server-Timing"] = f"learning;dur={latency_ms}"
    if request.method == "GET" and request.url.path.startswith(f"{API_PREFIX}/learning"):
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    learning_logger.info(json.dumps({
        "requestId": request_id,
        "operation": f"{request.method} {request.url.path}",
        "statusCode": response.status_code,
        "latencyMs": latency_ms,
        "errorCode": None if response.status_code < 400 else f"HTTP_{response.status_code}",
        "viewerType": "authenticated" if request.headers.get("Authorization") else "anonymous",
    }, ensure_ascii=False))
    return response


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    request.state.error_code = detail.get("code") if isinstance(detail, dict) else f"HTTP_{exc.status_code}"
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    request.state.error_code = "REQUEST_VALIDATION_ERROR"
    first = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first.get("loc", [])[1:])
    message = first.get("msg", "Request validation failed")
    if location:
        message = f"{location}: {message}"
    return JSONResponse(
        status_code=422,
        content={"detail": {"code": "REQUEST_VALIDATION_ERROR", "message": message}},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ALLOW_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id"],
    expose_headers=["Content-Disposition", "Server-Timing", "X-Request-Id"],
    max_age=600,
)
app.middleware("http")(security_response_headers)

app.include_router(common.router, prefix=API_PREFIX)
app.include_router(agent.router, prefix=API_PREFIX)
app.include_router(assets.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(learning.router, prefix=API_PREFIX)
app.include_router(operations.router, prefix=API_PREFIX)
app.include_router(privacy.router, prefix=API_PREFIX)
app.include_router(tools.router, prefix=API_PREFIX)
app.include_router(user_learning.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
