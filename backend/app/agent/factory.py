import json
import logging
from functools import lru_cache

from app.agent.governance import (
    AgentAdmissionGate,
    AgentCostGuard,
    AgentRuntimeGovernance,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.providers.fake import FakeProvider
from app.agent.providers.openai_compatible import OpenAICompatibleProvider
from app.core.config import get_agent_provider_settings


factory_logger = logging.getLogger("app.agent.provider")


@lru_cache(maxsize=16)
def _get_runtime_governance(
    per_user_concurrency: int,
    global_concurrency: int,
    queue_limit: int,
    queue_timeout_seconds: float,
    max_input_tokens: int,
    max_output_tokens: int,
    input_cny_per_million: float,
    output_cny_per_million: float,
    per_request_cost_cny: float,
    per_user_daily_cost_cny: float,
    global_daily_cost_cny: float,
    global_monthly_cost_cny: float,
) -> AgentRuntimeGovernance:
    return AgentRuntimeGovernance(
        admission=AgentAdmissionGate(
            per_user_limit=per_user_concurrency,
            global_limit=global_concurrency,
            queue_limit=queue_limit,
            queue_timeout_seconds=queue_timeout_seconds,
        ),
        cost=AgentCostGuard(
            max_input_tokens=max_input_tokens,
            max_output_tokens=max_output_tokens,
            input_cny_per_million=input_cny_per_million,
            output_cny_per_million=output_cny_per_million,
            per_request_cost_cny=per_request_cost_cny,
            per_user_daily_cost_cny=per_user_daily_cost_cny,
            global_daily_cost_cny=global_daily_cost_cny,
            global_monthly_cost_cny=global_monthly_cost_cny,
        ),
    )


def get_agent_orchestrator() -> AgentOrchestrator:
    try:
        settings = get_agent_provider_settings()
    except RuntimeError:
        factory_logger.warning(json.dumps({"event": "AGENT_PROVIDER_CONFIG_INVALID"}))
        return AgentOrchestrator(disabled_reason="not_configured")

    provider = None
    if settings.provider == "fake":
        provider = FakeProvider()
    elif settings.provider == "openai_compatible" and settings.live_enabled:
        provider = OpenAICompatibleProvider(
            base_url=settings.base_url,
            api_key=settings.api_key,
            model=settings.model,
            timeout_seconds=settings.timeout_seconds,
            max_retries=settings.max_retries,
            max_output_tokens=settings.max_output_tokens,
        )
    governance = _get_runtime_governance(
        settings.per_user_concurrency,
        settings.global_concurrency,
        settings.queue_limit,
        settings.queue_timeout_seconds,
        settings.max_input_tokens,
        settings.max_output_tokens,
        settings.input_cny_per_million,
        settings.output_cny_per_million,
        settings.per_request_cost_cny,
        settings.per_user_daily_cost_cny,
        settings.global_daily_cost_cny,
        settings.global_monthly_cost_cny,
    )
    return AgentOrchestrator(
        provider=provider,
        governance=governance,
        timeout_seconds=settings.timeout_seconds,
        max_output_chars=settings.max_output_chars,
        max_evidence_items=settings.max_evidence_items,
        max_evidence_chars=settings.max_evidence_chars,
        disabled_reason=(
            "not_configured"
            if settings.provider == "openai_compatible" and not settings.live_enabled
            else None
        ),
    )
