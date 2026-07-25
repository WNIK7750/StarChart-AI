import re
from ipaddress import ip_address
from urllib.parse import urlsplit

from app.agent.schemas import AgentStructuredResponse

ALLOWED_HREF_PATHS = {
    "index.html",
    "learn.html",
    "learn-node.html",
    "tools.html",
    "assistant.html",
    "settings.html",
}
PROVIDER_LINK_PATTERN = re.compile(
    r"(?i)(?:(?:https?|ftp|file|mailto|tel|sms|javascript|data|blob):|www\.|"
    r"\[[^\]]+\]\s*\()"
)
PROVIDER_DOMAIN_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])(?:[a-z0-9](?:[a-z0-9-]{0,62})\.)+"
    r"(?:[a-z]{2,63})"
    r"(?![A-Za-z0-9_-])"
)
PROVIDER_IPV4_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:\d{1,3}\.){3}\d{1,3}(?![A-Za-z0-9_-])"
)
PROVIDER_IPV6_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9_:])(?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}"
    r"(?![A-Za-z0-9_:])"
)
PROVIDER_CITATION_PATTERN = re.compile(
    r"(?i)(?:(?<![A-Za-z0-9_-])(?:learning_node|tool|page):"
    r"[A-Za-z0-9][A-Za-z0-9_.-]*(?![A-Za-z0-9_.-])|citationId\s*[:=])"
)
PROVIDER_SECRET_PATTERN = re.compile(
    r"(?i)(?:(?<![A-Za-z0-9_-])Bearer\s+[A-Za-z0-9._~+/=-]{8,}|"
    r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{12,}|"
    r"api[_ -]?key\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,})"
)
PROVIDER_INPUT_SECRET_PATTERN = re.compile(
    r"(?i)(?:"
    r"authorization\s*[:=]\s*\S{8,}|"
    r"(?<![A-Za-z0-9_-])Bearer\s+[A-Za-z0-9._~+/=-]{8,}|"
    r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{12,}|"
    r"api[_ -]?key\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,}|"
    r"(?:password|passwd|refresh[_ -]?token|access[_ -]?token|session[_ -]?token|cookie)"
    r"\s*[:=]\s*\S{8,}|"
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|"
    r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"
    r")"
)
PROVIDER_HTML_PATTERN = re.compile(
    r"(?i)<\s*/?\s*(?:a|abbr|address|article|aside|audio|base|blockquote|body|"
    r"br|button|canvas|caption|code|col|colgroup|data|datalist|dd|details|dialog|"
    r"div|dl|dt|em|embed|fieldset|figcaption|figure|footer|form|h[1-6]|head|"
    r"header|hgroup|hr|html|iframe|img|input|label|legend|li|link|main|map|mark|"
    r"menu|meta|meter|nav|noscript|object|ol|optgroup|option|output|p|picture|"
    r"pre|progress|q|script|section|select|slot|small|source|span|strong|style|"
    r"summary|svg|table|tbody|td|template|textarea|tfoot|th|thead|time|title|tr|"
    r"track|ul|var|video|wbr|[a-z][a-z0-9._]*-[a-z0-9._-]+)\b[^>]*>"
)
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def extract_grounded_dotted_terms(values: list[str] | tuple[str, ...]) -> set[str]:
    return {
        match.group(0).lower()
        for value in values
        for match in PROVIDER_DOMAIN_PATTERN.finditer(value)
    }


def contains_ip_address(value: str) -> bool:
    for pattern in (PROVIDER_IPV4_PATTERN, PROVIDER_IPV6_PATTERN):
        for match in pattern.finditer(value):
            try:
                ip_address(match.group(0))
            except ValueError:
                continue
            return True
    return False


def validate_provider_answer(
    answer: str,
    max_output_chars: int,
    *,
    allowed_dotted_terms: set[str] | None = None,
) -> str:
    value = answer.strip() if isinstance(answer, str) else ""
    if not value:
        raise ValueError("empty")
    if len(value) > max_output_chars:
        raise ValueError("too_long")
    if CONTROL_CHARACTER_PATTERN.search(value):
        raise ValueError("control_character")
    if PROVIDER_LINK_PATTERN.search(value):
        raise ValueError("link")
    if any(
        match.group(0).lower() not in (allowed_dotted_terms or set())
        for match in PROVIDER_DOMAIN_PATTERN.finditer(value)
    ):
        raise ValueError("domain")
    if contains_ip_address(value):
        raise ValueError("ip_address")
    if PROVIDER_CITATION_PATTERN.search(value):
        raise ValueError("fabricated_citation")
    if PROVIDER_SECRET_PATTERN.search(value) or PROVIDER_INPUT_SECRET_PATTERN.search(value):
        raise ValueError("secret_like_content")
    if PROVIDER_HTML_PATTERN.search(value):
        raise ValueError("html")
    return value


def validate_provider_user_message(message: str) -> str:
    value = message.strip() if isinstance(message, str) else ""
    if not value:
        raise ValueError("empty")
    if PROVIDER_INPUT_SECRET_PATTERN.search(value):
        raise ValueError("sensitive_input")
    return value


def is_allowed_internal_href(href: str) -> bool:
    if not isinstance(href, str) or not href or "\\" in href or CONTROL_CHARACTER_PATTERN.search(href):
        return False
    parsed = urlsplit(href)
    return (
        not parsed.scheme
        and not parsed.netloc
        and parsed.path in ALLOWED_HREF_PATHS
        and ".." not in parsed.path
    )


def validate_response(response: AgentStructuredResponse) -> AgentStructuredResponse:
    """Final response guardrail for deterministic and future LLM outputs."""
    response.cards = [
        card
        for card in response.cards
        if is_allowed_internal_href(card.href)
    ]
    response.citations = [
        citation
        for citation in response.citations
        if is_allowed_internal_href(citation.href)
    ]
    citation_ids = {citation.citationId for citation in response.citations}
    for card in response.cards:
        card.citationIds = [citation_id for citation_id in card.citationIds if citation_id in citation_ids]
    for step in response.workflowSteps:
        step.citationIds = [citation_id for citation_id in step.citationIds if citation_id in citation_ids]
        if step.targetHref and not is_allowed_internal_href(step.targetHref):
            step.targetHref = None
    return response
