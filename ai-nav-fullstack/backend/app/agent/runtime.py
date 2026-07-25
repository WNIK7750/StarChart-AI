from app.agent.schemas import (
    AgentRuntimeFeatures,
    AgentRuntimeProfile,
    AgentRuntimeProvider,
    AgentRuntimeSafety,
    AgentRuntimeTopology,
)
from app.core.config import (
    AGENT_RUNTIME_STATE_BACKEND,
    AGENT_SESSIONS_ENABLED,
    AGENT_STREAM_ENABLED,
    API_WORKERS,
    get_agent_provider_settings,
)


def get_agent_runtime_profile() -> AgentRuntimeProfile:
    try:
        settings = get_agent_provider_settings()
    except RuntimeError:
        provider = AgentRuntimeProvider(
            mode="invalid",
            model=None,
            live=False,
            configurationValid=False,
            upgradeModel=None,
            upgradeRatio=0,
        )
    else:
        if settings.provider == "openai_compatible":
            mode = "live" if settings.live_enabled else "configured_off"
        else:
            mode = settings.provider
        provider = AgentRuntimeProvider(
            mode=mode,
            model=settings.model,
            live=settings.provider == "openai_compatible" and settings.live_enabled,
            configurationValid=True,
            upgradeModel=settings.upgrade_model,
            upgradeRatio=settings.upgrade_ratio,
        )

    return AgentRuntimeProfile(
        provider=provider,
        features=AgentRuntimeFeatures(
            stream=AGENT_STREAM_ENABLED,
            sessions=AGENT_SESSIONS_ENABLED,
            responseReplay=True,
            observability=True,
            openAICompatibleIncremental=False,
        ),
        safety=AgentRuntimeSafety(),
        topology=AgentRuntimeTopology(
            declaredWorkers=API_WORKERS,
            stateBackend=AGENT_RUNTIME_STATE_BACKEND,
        ),
    )
