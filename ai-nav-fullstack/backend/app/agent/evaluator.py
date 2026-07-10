from app.agent.schemas import AgentStructuredResponse


def validate_response(response: AgentStructuredResponse) -> AgentStructuredResponse:
    """Final response guardrail placeholder.

    Future implementations should verify every href comes from a site route,
    the learning database, or the tool database. For now this function preserves
    the module boundary and keeps generation separate from validation.
    """
    return response
