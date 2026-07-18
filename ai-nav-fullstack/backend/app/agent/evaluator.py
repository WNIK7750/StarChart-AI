from app.agent.schemas import AgentStructuredResponse

ALLOWED_HREF_PREFIXES = (
    "index.html",
    "learn.html",
    "learn-node.html",
    "tools.html",
)


def validate_response(response: AgentStructuredResponse) -> AgentStructuredResponse:
    """Final response guardrail for deterministic and future LLM outputs."""
    response.cards = [
        card
        for card in response.cards
        if card.href.startswith(ALLOWED_HREF_PREFIXES) and "://" not in card.href
    ]
    response.citations = [
        citation
        for citation in response.citations
        if citation.href.startswith(ALLOWED_HREF_PREFIXES) and "://" not in citation.href
    ]
    citation_ids = {citation.citationId for citation in response.citations}
    for card in response.cards:
        card.citationIds = [citation_id for citation_id in card.citationIds if citation_id in citation_ids]
    for step in response.workflowSteps:
        step.citationIds = [citation_id for citation_id in step.citationIds if citation_id in citation_ids]
        if step.targetHref and (
            not step.targetHref.startswith(ALLOWED_HREF_PREFIXES) or "://" in step.targetHref
        ):
            step.targetHref = None
    return response
