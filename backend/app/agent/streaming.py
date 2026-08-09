import json
from collections.abc import Iterator

from app.agent.schemas import AgentStreamEvent, AgentStructuredResponse


DEFAULT_ANSWER_CHUNK_CHARS = 80


def iter_answer_chunks(
    answer: str,
    *,
    chunk_chars: int = DEFAULT_ANSWER_CHUNK_CHARS,
) -> Iterator[str]:
    """Split visible answer text to the transport contract's delta limit."""
    if not 1 <= chunk_chars <= 1000:
        raise ValueError("chunk_chars must be between 1 and 1000")
    for offset in range(0, len(answer), chunk_chars):
        yield answer[offset : offset + chunk_chars]


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
    sequence = 0
    yield AgentStreamEvent(
        event="response.started",
        sequence=sequence,
        requestId=request_id,
    )
    for chunk in iter_answer_chunks(response.answer, chunk_chars=chunk_chars):
        sequence += 1
        yield AgentStreamEvent(
            event="response.answer.delta",
            sequence=sequence,
            requestId=request_id,
            delta=chunk,
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
