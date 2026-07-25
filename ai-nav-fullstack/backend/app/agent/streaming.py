import json
from collections.abc import Iterator

from app.agent.schemas import AgentStreamEvent, AgentStructuredResponse


DEFAULT_ANSWER_CHUNK_CHARS = 80


def project_response_events(
    response: AgentStructuredResponse,
    request_id: str,
    *,
    chunk_chars: int = DEFAULT_ANSWER_CHUNK_CHARS,
) -> Iterator[AgentStreamEvent]:
    """Project one canonical Agent result into transport events.

    Stage 2 starts with buffered projection so JSON and SSE cannot diverge.
    A later Provider transport may emit real deltas behind this same contract.
    """
    if not 1 <= chunk_chars <= 1000:
        raise ValueError("chunk_chars must be between 1 and 1000")

    sequence = 0
    yield AgentStreamEvent(
        event="response.started",
        sequence=sequence,
        requestId=request_id,
    )
    for offset in range(0, len(response.answer), chunk_chars):
        sequence += 1
        yield AgentStreamEvent(
            event="response.answer.delta",
            sequence=sequence,
            requestId=request_id,
            delta=response.answer[offset : offset + chunk_chars],
        )
    sequence += 1
    yield AgentStreamEvent(
        event="response.completed",
        sequence=sequence,
        requestId=request_id,
        response=response,
    )


def encode_sse(event: AgentStreamEvent) -> bytes:
    payload = json.dumps(
        event.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event.event}\ndata: {payload}\n\n".encode("utf-8")
