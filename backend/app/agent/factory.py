import json
import logging
from functools import lru_cache
from urllib.parse import urlsplit

from langchain_openai import ChatOpenAI

from app.agent.governance import (
    AgentAdmissionGate,
    AgentCostGuard,
    AgentRuntimeGovernance,
)
from app.agent.orchestrator import AgentOrchestrator
from app.agent.loop import SiteAgentLoopRuntime
from app.agent.web_search import DashScopeNativeWebSearch
from app.core.config import get_agent_provider_settings
from app.users.model_settings.service import ResolvedAgentModelSettings


factory_logger = logging.getLogger("app.agent.provider")


def _provider_model_options(base_url: str) -> dict[str, object]:
    """Keep provider-specific transport quirks outside the Agent workflow."""
    hostname = (urlsplit(base_url).hostname or "").lower()
    if hostname == "dashscope.aliyuncs.com" or hostname.endswith(
        ".maas.aliyuncs.com"
    ):
        return {"extra_body": {"enable_thinking": False}}
    return {}


def build_user_agent_loop(
    settings: ResolvedAgentModelSettings,
) -> SiteAgentLoopRuntime:
    """Adapt a Users-owned credential into the Agent runtime without leaking it."""
    model_options = {
        "base_url": settings.base_url,
        "api_key": settings.api_key,
        "model": settings.model_id,
        # Complex recommendations require several bounded model turns. A slightly
        # longer single attempt is more predictable than an automatic retry that
        # repeats an entire slow provider request inside the Agent loop.
        "timeout": 30,
        "max_retries": 0,
        "temperature": 0.1,
        **_provider_model_options(settings.base_url),
    }
    if settings.max_output_tokens is not None:
        model_options["max_tokens"] = settings.max_output_tokens
    model = ChatOpenAI(**model_options)
    hostname = (urlsplit(settings.base_url).hostname or "").lower()
    web_search = None
    if hostname == "dashscope.aliyuncs.com" or hostname.endswith(".maas.aliyuncs.com"):
        web_search = DashScopeNativeWebSearch(
            base_url=settings.base_url,
            api_key=settings.api_key,
            model=settings.model_id,
        )
    return SiteAgentLoopRuntime(
        model=model,
        provider_name=settings.provider_name,
        model_name=settings.model_display_name,
        max_output_chars=12000,
        broad_prefetch=True,
        web_search=web_search,
    )


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
        governance=governance,
        timeout_seconds=settings.timeout_seconds,
        # User-owned models are not constrained by a platform cost budget. Keep a
        # finite UX deadline, but allow the observable multi-step Agent path to
        # complete for slower OpenAI-compatible providers.
        loop_timeout_seconds=max(90.0, settings.timeout_seconds * 5),
        max_output_chars=settings.max_output_chars,
        max_evidence_items=settings.max_evidence_items,
        max_evidence_chars=settings.max_evidence_chars,
        # Model execution is user-owned. Environment Provider values are never
        # a silent default; without a resolved user model this runtime can only
        # return an explicit evidence-based fallback.
        disabled_reason="not_configured",
    )
