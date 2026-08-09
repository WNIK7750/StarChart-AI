import asyncio

from app.agent.providers.base import (
    AgentProvider,
    ProviderError,
    ProviderRequest,
    ProviderResult,
    ProviderStreamCompleted,
    ProviderTextDelta,
)


class FakeProvider(AgentProvider):
    """Controllable provider used only by isolated contract tests."""

    name = "fake"

    def __init__(
        self,
        *,
        answer: str = "这是基于站内证据生成的测试回答。",
        model: str = "fake-agent-model",
        failure: ProviderError | None = None,
        delay_seconds: float = 0,
        stream_chunks: tuple[str, ...] | None = None,
        stream_delay_seconds: float = 0,
    ):
        self.answer = answer
        self.model = model
        self.failure = failure
        self.delay_seconds = delay_seconds
        self.stream_chunks = stream_chunks
        self.stream_delay_seconds = stream_delay_seconds
        self.requests: list[ProviderRequest] = []
        self.streamed_chunks: list[str] = []
        self.stream_cancelled = asyncio.Event()

    async def generate(self, request: ProviderRequest) -> ProviderResult:
        self.requests.append(request)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.failure:
            raise self.failure
        return ProviderResult(answer=self.answer, provider=self.name, model=self.model)

    async def stream_generate(self, request: ProviderRequest):
        self.requests.append(request)
        completed_normally = False
        try:
            if self.failure:
                raise self.failure
            chunks = self.stream_chunks or (self.answer,)
            for chunk in chunks:
                if self.stream_delay_seconds:
                    await asyncio.sleep(self.stream_delay_seconds)
                self.streamed_chunks.append(chunk)
                yield ProviderTextDelta(text=chunk)
            yield ProviderStreamCompleted(
                result=ProviderResult(
                    answer="".join(chunks),
                    provider=self.name,
                    model=self.model,
                )
            )
            completed_normally = True
        except asyncio.CancelledError:
            self.stream_cancelled.set()
            raise
        finally:
            if not completed_normally:
                self.stream_cancelled.set()
