from __future__ import annotations

import re

from app.agent.schemas import AgentHistoryMessage


_WHITESPACE = re.compile(r"\s+")


def _compact_text(value: str, limit: int) -> str:
    text = _WHITESPACE.sub(" ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)].rstrip()}…"


def compact_conversation_history(
    history: tuple[AgentHistoryMessage, ...],
    *,
    recent_exchanges: int = 2,
    max_reports: int = 4,
) -> tuple[AgentHistoryMessage, ...]:
    """Project one conversation into old final reports plus recent raw turns.

    Persisted messages remain the source of truth. This projection never crosses
    a session boundary and never includes tools, traces, diagnostic notes or
    provider payloads because those are not stored as conversation messages.
    """

    if not history:
        return ()
    raw_count = max(0, recent_exchanges) * 2
    if len(history) <= raw_count:
        return history

    older = history[:-raw_count] if raw_count else history
    recent = history[-raw_count:] if raw_count else ()
    reports: list[AgentHistoryMessage] = []
    index = 0
    while index + 1 < len(older):
        user = older[index]
        assistant = older[index + 1]
        if user.role != "user" or assistant.role != "assistant":
            index += 1
            continue
        reports.append(AgentHistoryMessage(
            role="assistant",
            content=(
                "[当前对话内的已完成任务记录]\n"
                f"用户目标：{_compact_text(user.content, 180)}\n"
                f"最终结果：{_compact_text(assistant.content, 620)}"
            ),
        ))
        index += 2

    if max_reports >= 0:
        reports = reports[-max_reports:]
    return (*reports, *recent)
