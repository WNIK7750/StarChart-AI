import asyncio
from contextlib import suppress
import hashlib
import hmac
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.api.v1.dependencies.authorization import require_permission
from app.api.v1.routers.auth import _client_ip
from app.agent.factory import build_user_agent_loop, get_agent_orchestrator
from app.agent.governance import AgentAdmissionGate, AgentGovernanceRejected
from app.agent.orchestrator import AgentOrchestrator
from app.agent.observability import get_agent_metrics
from app.agent.replay import (
    AgentReplayConflict,
    get_agent_replay_singleflight,
    get_agent_response_replay_cache,
    request_fingerprint,
)
from app.agent.schemas import (
    AgentCapabilities,
    AgentChatRequest,
    AgentErrorResponse,
    AgentGuestChatRequest,
    AgentMetricsResponse,
    AgentLongConversationDetailResponse,
    AgentLongConversationListResponse,
    AgentLongConversationUpdateResponse,
    AgentSessionCreate,
    AgentSessionCreateResponse,
    AgentSessionDetailResponse,
    AgentSessionListResponse,
    AgentSessionUpgradeResponse,
    AgentSessionUpdate,
    AgentSessionUpdateResponse,
    AgentStreamEvent,
    AgentProgress,
    AgentStructuredResponse,
    AgentRuntimeProfile,
)
from app.agent.sessions import AgentSessionError, get_agent_session_service
from app.agent.runtime import get_agent_runtime_profile
from app.agent.service import needs_user_context
from app.agent.streaming import encode_sse, iter_answer_chunks
from app.core.config import (
    AGENT_GUEST_CHAT_ENABLED,
    AGENT_SESSIONS_ENABLED,
    AGENT_STREAM_BUFFER_EVENTS,
    AGENT_STREAM_ENABLED,
    PRIVACY_POLICY_VERSION,
    SECRET_KEY,
    TRUSTED_PROXY_CIDRS,
)
from app.users.assets.facade import get_user_assets_facade
from app.users.assets.schemas import WorkflowCreate, WorkflowCreateResponse
from app.users.common import UsersError, users_error_detail
from app.users.context.facade import get_user_context_facade
from app.users.model_settings.service import get_agent_model_settings_service

router = APIRouter(prefix="/agent", tags=["agent"])
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
USER_CONTEXT_TIMEOUT_SECONDS = 1.0
GUEST_AGENT_TIMEOUT_SECONDS = 15.0
_guest_orchestrator = AgentOrchestrator()
_guest_admission_gate = AgentAdmissionGate(
    per_user_limit=1,
    global_limit=8,
    queue_limit=16,
    queue_timeout_seconds=2,
)


@router.get("/capabilities", response_model=AgentCapabilities)
def agent_capabilities():
    return AgentCapabilities(
        stream=AGENT_STREAM_ENABLED,
        sessions=AGENT_SESSIONS_ENABLED,
    )


def _session_error(exc: AgentSessionError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


def _replay_conflict(exc: AgentReplayConflict) -> None:
    get_agent_metrics().record_request_id_conflict()
    raise HTTPException(
        status_code=409,
        detail={
            "code": "AGENT_REQUEST_ID_CONFLICT",
            "message": "请求标识已被其他内容使用，请重新发送",
        },
    ) from exc


def _require_sessions_enabled() -> None:
    if not AGENT_SESSIONS_ENABLED:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AGENT_SESSIONS_DISABLED",
                "message": "短期会话当前未启用",
            },
        )


def _safe_request_id(request: Request) -> str:
    value = request.headers.get("X-Request-Id", "")
    return value if REQUEST_ID_PATTERN.fullmatch(value) else uuid4().hex


def _require_guest_agent_enabled() -> None:
    if not AGENT_GUEST_CHAT_ENABLED:
        raise HTTPException(status_code=404, detail="Not Found")


def _guest_client_key(request: Request) -> str:
    client_ip = _client_ip(request, TRUSTED_PROXY_CIDRS)
    digest = hmac.new(
        SECRET_KEY.encode("utf-8"),
        client_ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]
    return f"guest:{digest}"


async def _wait_for_disconnect(request: Request) -> None:
    while not await request.is_disconnected():
        await asyncio.sleep(0.05)


def _consume_background_task(task: asyncio.Task) -> None:
    try:
        task.result()
    except (asyncio.CancelledError, Exception):
        pass


async def _respond_until_disconnect(request: Request, response_task: asyncio.Task):
    disconnect_task = asyncio.create_task(_wait_for_disconnect(request))
    try:
        done, _pending = await asyncio.wait(
            {response_task, disconnect_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if response_task in done:
            result = await response_task
            # Cancelling Starlette's receive while BaseHTTPMiddleware is relaying
            # the request can consume its terminal message and deadlock the
            # response. Let the watcher observe response completion naturally.
            disconnect_task.add_done_callback(_consume_background_task)
            return result
        response_task.cancel()
        with suppress(asyncio.CancelledError):
            await response_task
        raise HTTPException(
            status_code=499,
            detail={"code": "AGENT_REQUEST_CANCELLED", "message": "客户端已取消请求"},
        )
    except BaseException:
        if not response_task.done():
            response_task.cancel()
        if not disconnect_task.done():
            disconnect_task.cancel()
        with suppress(asyncio.CancelledError):
            await response_task
        with suppress(asyncio.CancelledError):
            await disconnect_task
        raise


async def _run_agent_request(
    payload: AgentChatRequest,
    current_user: dict,
    orchestrator: AgentOrchestrator,
    request_id: str,
    *,
    on_answer_delta=None,
    on_progress=None,
) -> AgentStructuredResponse:
    async with get_agent_replay_singleflight().slot(current_user["id"], request_id):
        return await _run_serialized_agent_request(
            payload,
            current_user,
            orchestrator,
            request_id,
            on_answer_delta=on_answer_delta,
            on_progress=on_progress,
        )


async def _run_serialized_agent_request(
    payload: AgentChatRequest,
    current_user: dict,
    orchestrator: AgentOrchestrator,
    request_id: str,
    *,
    on_answer_delta=None,
    on_progress=None,
) -> AgentStructuredResponse:
    session_service = None
    history = ()
    if payload.sessionId:
        _require_sessions_enabled()
        session_service = get_agent_session_service()
        try:
            await run_in_threadpool(
                session_service.require_owned,
                current_user["id"],
                payload.sessionId,
            )
            history = await run_in_threadpool(
                session_service.context,
                current_user["id"],
                payload.sessionId,
            )
        except AgentSessionError as exc:
            _session_error(exc)

    fingerprint = request_fingerprint(payload, history=history)
    replay_cache = get_agent_response_replay_cache()
    try:
        replayed = replay_cache.get(
            current_user["id"],
            request_id,
            fingerprint,
        )
    except AgentReplayConflict as exc:
        _replay_conflict(exc)
    if replayed is not None:
        get_agent_metrics().record_replay_hit()
        return replayed

    provider_allowed = bool(
        current_user.get("privacyConsentAction") == "granted"
        and current_user.get("privacyConsentPolicyVersion") == PRIVACY_POLICY_VERSION
    )
    user_agent_loop = None
    if provider_allowed:
        try:
            resolved_model = await run_in_threadpool(
                get_agent_model_settings_service().resolve,
                current_user["id"],
                current_user.get("user_uid") or f"user:{current_user['id']}",
            )
            if resolved_model is not None:
                user_agent_loop = build_user_agent_loop(resolved_model)
        except UsersError:
            user_agent_loop = None
    user_context = None
    uses_model_loop = (
        isinstance(orchestrator, AgentOrchestrator)
        and (user_agent_loop is not None or orchestrator.agent_loop is not None)
    )
    if uses_model_loop or needs_user_context(payload):
        try:
            user_context = await asyncio.wait_for(
                run_in_threadpool(
                    get_user_context_facade().for_agent,
                    current_user["id"],
                ),
                timeout=USER_CONTEXT_TIMEOUT_SECONDS,
            )
        except Exception:
            user_context = None
    response_options = {
        "history": history,
        "request_id": request_id,
        "user_key": f"user:{current_user['id']}",
        "provider_allowed": provider_allowed,
    }
    if on_answer_delta is not None:
        response_options["on_answer_delta"] = on_answer_delta
    if on_progress is not None:
        response_options["on_progress"] = on_progress
    if user_agent_loop is not None:
        response_options["agent_loop_override"] = user_agent_loop
    result = await orchestrator.respond(payload, user_context, **response_options)

    async def finalize_response() -> None:
        nonlocal fingerprint, history
        if session_service and payload.sessionId:
            await run_in_threadpool(
                session_service.append_exchange,
                current_user["id"],
                payload.sessionId,
                request_id,
                payload.message,
                result.answer,
            )
            history = await run_in_threadpool(
                session_service.context,
                current_user["id"],
                payload.sessionId,
            )
            fingerprint = request_fingerprint(payload, history=history)
        replay_cache.put(
            current_user["id"],
            request_id,
            fingerprint,
            result,
        )

    finalization = asyncio.create_task(finalize_response())
    try:
        await asyncio.shield(finalization)
    except asyncio.CancelledError:
        await finalization
        raise
    except AgentSessionError as exc:
        _session_error(exc)
    except AgentReplayConflict as exc:
        _replay_conflict(exc)
    return result


async def _run_guest_agent_request(
    payload: AgentGuestChatRequest,
    request_id: str,
    guest_key: str,
) -> AgentStructuredResponse:
    async with get_agent_replay_singleflight().slot(guest_key, request_id):
        return await _run_serialized_guest_agent_request(payload, request_id, guest_key)


async def _run_serialized_guest_agent_request(
    payload: AgentGuestChatRequest,
    request_id: str,
    guest_key: str,
) -> AgentStructuredResponse:
    request_payload = AgentChatRequest(
        message=payload.message,
        pageContext=payload.pageContext,
    )
    history = tuple(payload.history)
    fingerprint = request_fingerprint(request_payload, history=history)
    replay_cache = get_agent_response_replay_cache()
    try:
        replayed = replay_cache.get(guest_key, request_id, fingerprint)
    except AgentReplayConflict as exc:
        _replay_conflict(exc)
    if replayed is not None:
        get_agent_metrics().record_replay_hit()
        return replayed

    try:
        async with _guest_admission_gate.slot(guest_key):
            result = await asyncio.wait_for(
                _guest_orchestrator.respond_guest(
                    request_payload,
                    history=history,
                    request_id=request_id,
                    guest_key=guest_key,
                ),
                timeout=GUEST_AGENT_TIMEOUT_SECONDS,
            )
    except AgentGovernanceRejected as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AGENT_CAPACITY_LIMITED",
                "message": "助手当前繁忙，请稍后重试",
            },
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "AGENT_REQUEST_TIMEOUT",
                "message": "助手响应超时，请稍后重试",
            },
        ) from exc

    try:
        replay_cache.put(guest_key, request_id, fingerprint, result)
    except AgentReplayConflict as exc:
        _replay_conflict(exc)
    return result


@router.post(
    "/sessions",
    status_code=201,
    response_model=AgentSessionCreateResponse,
)
def create_agent_session(
    payload: AgentSessionCreate,
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        return get_agent_session_service().create(current_user["id"], payload.title)
    except AgentSessionError as exc:
        _session_error(exc)


@router.post(
    "/sessions/draft",
    response_model=AgentSessionCreateResponse,
)
def ensure_agent_session_draft(
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    return get_agent_session_service().ensure_draft(current_user["id"])


@router.get("/sessions", response_model=AgentSessionListResponse)
def list_agent_sessions(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=10000),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    return get_agent_session_service().list(current_user["id"], limit, offset)


@router.post(
    "/sessions/{session_uid}/upgrade",
    response_model=AgentSessionUpgradeResponse,
)
def upgrade_agent_session(
    session_uid: str = Path(min_length=8, max_length=80, pattern=r"^ags_[a-f0-9]+$"),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        return get_agent_session_service().upgrade(current_user["id"], session_uid)
    except AgentSessionError as exc:
        _session_error(exc)


@router.get(
    "/sessions/{session_uid}",
    response_model=AgentSessionDetailResponse,
)
def get_agent_session(
    session_uid: str = Path(min_length=8, max_length=80, pattern=r"^ags_[a-f0-9]+$"),
    message_limit: int = Query(default=50, alias="messageLimit", ge=1, le=100),
    message_offset: int = Query(default=0, alias="messageOffset", ge=0, le=10000),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        return get_agent_session_service().get(
            current_user["id"],
            session_uid,
            message_limit,
            message_offset,
        )
    except AgentSessionError as exc:
        _session_error(exc)


@router.patch(
    "/sessions/{session_uid}",
    response_model=AgentSessionUpdateResponse,
)
def update_agent_session(
    payload: AgentSessionUpdate,
    session_uid: str = Path(min_length=8, max_length=80, pattern=r"^ags_[a-f0-9]+$"),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        return get_agent_session_service().update(
            current_user["id"],
            session_uid,
            title=payload.title,
            pinned=payload.pinned,
        )
    except AgentSessionError as exc:
        _session_error(exc)


@router.delete("/sessions/{session_uid}", status_code=204)
def delete_agent_session(
    session_uid: str = Path(min_length=8, max_length=80, pattern=r"^ags_[a-f0-9]+$"),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        get_agent_session_service().delete(current_user["id"], session_uid)
    except AgentSessionError as exc:
        _session_error(exc)


@router.get(
    "/long-conversations",
    response_model=AgentLongConversationListResponse,
)
def list_agent_long_conversations(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=10000),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    return get_agent_session_service().list_long(current_user["id"], limit, offset)


@router.get(
    "/long-conversations/{conversation_uid}",
    response_model=AgentLongConversationDetailResponse,
)
def get_agent_long_conversation(
    conversation_uid: str = Path(
        min_length=8,
        max_length=80,
        pattern=r"^agl_[a-f0-9]+$",
    ),
    message_limit: int = Query(default=50, alias="messageLimit", ge=1, le=100),
    message_offset: int = Query(default=0, alias="messageOffset", ge=0, le=10000),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        return get_agent_session_service().get_long(
            current_user["id"],
            conversation_uid,
            message_limit,
            message_offset,
        )
    except AgentSessionError as exc:
        _session_error(exc)


@router.patch(
    "/long-conversations/{conversation_uid}",
    response_model=AgentLongConversationUpdateResponse,
)
def update_agent_long_conversation(
    payload: AgentSessionUpdate,
    conversation_uid: str = Path(
        min_length=8,
        max_length=80,
        pattern=r"^agl_[a-f0-9]+$",
    ),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        return get_agent_session_service().update_long(
            current_user["id"],
            conversation_uid,
            title=payload.title,
            pinned=payload.pinned,
        )
    except AgentSessionError as exc:
        _session_error(exc)


@router.delete("/long-conversations/{conversation_uid}", status_code=204)
def delete_agent_long_conversation(
    conversation_uid: str = Path(
        min_length=8,
        max_length=80,
        pattern=r"^agl_[a-f0-9]+$",
    ),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    _require_sessions_enabled()
    try:
        get_agent_session_service().delete_long(
            current_user["id"],
            conversation_uid,
        )
    except AgentSessionError as exc:
        _session_error(exc)


@router.get("/operations/metrics", response_model=AgentMetricsResponse)
def agent_metrics(
    _: dict = Depends(require_permission("users:manage")),
):
    return get_agent_metrics().snapshot()


@router.get("/operations/runtime", response_model=AgentRuntimeProfile)
def agent_runtime(
    _: dict = Depends(require_permission("users:manage")),
):
    return get_agent_runtime_profile()


@router.post(
    "/guest/chat",
    response_model=AgentStructuredResponse,
    include_in_schema=AGENT_GUEST_CHAT_ENABLED,
    responses={
        404: {"model": AgentErrorResponse},
        409: {"model": AgentErrorResponse},
        422: {"model": AgentErrorResponse},
        499: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
        504: {"model": AgentErrorResponse},
    },
)
async def agent_guest_chat(
    payload: AgentGuestChatRequest,
    request: Request,
    response: Response,
):
    _require_guest_agent_enabled()
    request_id = _safe_request_id(request)
    response.headers["X-Request-Id"] = request_id
    response_task = asyncio.create_task(
        _run_guest_agent_request(
            payload,
            request_id,
            _guest_client_key(request),
        )
    )
    return await _respond_until_disconnect(request, response_task)


@router.post(
    "/chat",
    response_model=AgentStructuredResponse,
    responses={
        401: {"model": AgentErrorResponse},
        403: {"model": AgentErrorResponse},
        409: {"model": AgentErrorResponse},
        422: {"model": AgentErrorResponse},
        499: {"model": AgentErrorResponse},
    },
)
async def agent_chat(
    payload: AgentChatRequest,
    request: Request,
    response: Response,
    current_user: dict = Depends(require_permission("agent:chat")),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    request_id = _safe_request_id(request)
    response.headers["X-Request-Id"] = request_id
    response_task = asyncio.create_task(
        _run_agent_request(payload, current_user, orchestrator, request_id)
    )
    return await _respond_until_disconnect(request, response_task)


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={
        401: {"model": AgentErrorResponse},
        403: {"model": AgentErrorResponse},
        409: {"model": AgentErrorResponse},
        422: {"model": AgentErrorResponse},
        499: {"model": AgentErrorResponse},
        503: {"model": AgentErrorResponse},
    },
)
async def agent_chat_stream(
    payload: AgentChatRequest,
    request: Request,
    current_user: dict = Depends(require_permission("agent:chat")),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    if not AGENT_STREAM_ENABLED:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AGENT_STREAM_DISABLED",
                "message": "流式回答当前未启用，请使用普通回答接口",
            },
        )

    request_id = _safe_request_id(request)

    async def event_stream():
        event_queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue(
            maxsize=AGENT_STREAM_BUFFER_EVENTS
        )

        async def on_answer_delta(delta: str) -> None:
            # A bounded queue links Provider production to network consumption.
            # When the client is slow, queue.put pauses the producer.
            await event_queue.put(("delta", delta))

        async def on_progress(progress: AgentProgress) -> None:
            await event_queue.put(("progress", progress))

        response_task = asyncio.create_task(
            _run_agent_request(
                payload,
                current_user,
                orchestrator,
                request_id,
                on_answer_delta=on_answer_delta,
                on_progress=on_progress,
            )
        )
        disconnect_task = asyncio.create_task(_wait_for_disconnect(request))
        delta_task = None
        sequence = 0
        emitted_incremental_delta = False
        try:
            yield encode_sse(
                AgentStreamEvent(
                    event="response.started",
                    sequence=sequence,
                    requestId=request_id,
                )
            )
            await asyncio.sleep(0)

            while True:
                delta_task = asyncio.create_task(event_queue.get())
                done, _pending = await asyncio.wait(
                    {response_task, disconnect_task, delta_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if disconnect_task in done:
                    delta_task.cancel()
                    response_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await delta_task
                    with suppress(asyncio.CancelledError):
                        await response_task
                    return

                if delta_task in done:
                    item_type, item = delta_task.result()
                    sequence += 1
                    if item_type == "progress":
                        yield encode_sse(AgentStreamEvent(
                            event="agent.progress", sequence=sequence,
                            requestId=request_id, progress=item,
                        ))
                    else:
                        emitted_incremental_delta = True
                        sequence -= 1
                        for chunk in iter_answer_chunks(item):
                            sequence += 1
                            yield encode_sse(AgentStreamEvent(
                                event="response.answer.delta", sequence=sequence,
                                requestId=request_id, delta=chunk,
                            ))
                    await asyncio.sleep(0)
                    continue

                # The Provider can finish in the same loop turn as its final
                # queue put. Give the waiting consumer one turn so the last
                # validated delta is never skipped before completion.
                await asyncio.sleep(0)
                if delta_task.done():
                    item_type, item = delta_task.result()
                    sequence += 1
                    if item_type == "progress":
                        yield encode_sse(AgentStreamEvent(
                            event="agent.progress", sequence=sequence,
                            requestId=request_id, progress=item,
                        ))
                    else:
                        emitted_incremental_delta = True
                        sequence -= 1
                        for chunk in iter_answer_chunks(item):
                            sequence += 1
                            yield encode_sse(AgentStreamEvent(
                                event="response.answer.delta", sequence=sequence,
                                requestId=request_id, delta=chunk,
                            ))
                    await asyncio.sleep(0)
                    continue

                delta_task.cancel()
                with suppress(asyncio.CancelledError):
                    await delta_task
                result = await response_task
                # As in the JSON path, do not cancel Starlette's receive watcher
                # after successful completion; let it observe the terminal
                # request message without stealing it from middleware.
                disconnect_task.add_done_callback(_consume_background_task)
                disconnect_task = None

                if not emitted_incremental_delta and result.answer:
                    for chunk in iter_answer_chunks(result.answer):
                        sequence += 1
                        yield encode_sse(AgentStreamEvent(
                            event="response.answer.delta", sequence=sequence,
                            requestId=request_id, delta=chunk,
                        ))
                sequence += 1
                yield encode_sse(AgentStreamEvent(
                    event="response.completed", sequence=sequence,
                    requestId=request_id, response=result,
                ))
                return
        finally:
            if not response_task.done():
                response_task.cancel()
                with suppress(asyncio.CancelledError):
                    await response_task
            if delta_task is not None and not delta_task.done():
                delta_task.cancel()
                with suppress(asyncio.CancelledError):
                    await delta_task
            if disconnect_task is not None and not disconnect_task.done():
                disconnect_task.cancel()
                with suppress(asyncio.CancelledError):
                    await disconnect_task

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-Id": request_id,
        },
    )


@router.post("/workflows/save", status_code=201, response_model=WorkflowCreateResponse)
def save_agent_workflow(
    payload: WorkflowCreate,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    current_user: dict = Depends(require_permission("agent:chat")),
):
    if payload.sourceType != "agent":
        raise HTTPException(
            status_code=422,
            detail={"code": "AGENT_WORKFLOW_SOURCE_INVALID", "message": "Agent 保存命令只接受 agent 来源"},
        )
    context = {
        "actorUserId": current_user["id"],
        "targetUserId": current_user["id"],
        "ipAddress": request.client.host if request.client else None,
        "userAgent": request.headers.get("User-Agent"),
    }
    try:
        return get_user_assets_facade().save_workflow(
            current_user["id"],
            payload.model_dump(),
            idempotency_key,
            context,
        )
    except UsersError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=users_error_detail(exc),
        ) from exc
