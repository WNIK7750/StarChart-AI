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
    return response
