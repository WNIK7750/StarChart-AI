from dataclasses import dataclass
from collections.abc import AsyncIterator
from typing import Literal, Protocol, runtime_checkable

from app.agent.schemas import AgentHistoryRole


ProviderFailureKind = Literal[
    "not_configured",
    "cancelled",
    "timeout",
    "authentication",
    "rate_limited",
    "unavailable",
    "invalid_output",
    "sensitive_input",
]


@dataclass(frozen=True, slots=True)
class AgentEvidenceItem:
    citation_id: str
    source_type: str
    source_key: str
    title: str
    summary: str
    href: str


@dataclass(frozen=True, slots=True)
class ProviderConversationMessage:
    role: AgentHistoryRole
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"user", "assistant"}:
            raise ValueError("provider conversation role must be user or assistant")
        if not isinstance(self.content, str) or not 1 <= len(self.content) <= 12000:
            raise ValueError("provider conversation content must contain 1 to 12000 characters")


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    request_id: str
    prompt_version: str
    system_instruction: str
    user_message: str
    evidence: tuple[AgentEvidenceItem, ...]
    max_output_chars: int
    history: tuple[ProviderConversationMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderResult:
    answer: str
    provider: str
    model: str
    attempts: int = 1
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ProviderTextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ProviderStreamCompleted:
    result: ProviderResult


ProviderStreamEvent = ProviderTextDelta | ProviderStreamCompleted


class ProviderError(RuntimeError):
    def __init__(
        self,
        kind: ProviderFailureKind,
        safe_message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        attempts: int = 1,
    ):
        super().__init__(safe_message)
        self.kind = kind
        self.safe_message = safe_message
        self.retryable = retryable
        self.status_code = status_code
        self.attempts = attempts


class AgentProvider(Protocol):
    name: str
    model: str

    async def generate(self, request: ProviderRequest) -> ProviderResult: ...


@runtime_checkable
class StreamingAgentProvider(Protocol):
    def stream_generate(
        self,
        request: ProviderRequest,
    ) -> AsyncIterator[ProviderStreamEvent]: ...
