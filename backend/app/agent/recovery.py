from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.agent.evaluator import validate_provider_answer
from app.agent.schemas import AgentLinkCard


MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]\r\n]{1,240})\]\([^\r\n)]*\)")
AUTOLINK_PATTERN = re.compile(
    r"<(?:(?:https?|ftp|file|mailto|tel|sms):[^>\r\n]+)>",
    flags=re.IGNORECASE,
)
RAW_LINK_PATTERN = re.compile(
    r"(?i)(?:(?:https?|ftp|file|mailto|tel|sms|javascript|data|blob):\S+|www\.\S+)"
)
HTML_TAG_PATTERN = re.compile(r"<[^>\r\n]{1,500}>")
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True, slots=True)
class AnswerRecoveryResult:
    answer: str
    strategy: Literal["unchanged", "references_to_cards"]
    validation_reason: str | None = None


def normalize_inline_links(answer: str) -> str:
    """Move untrusted inline destinations out of prose while keeping labels.

    The response contract exposes destinations through separately validated cards.
    Model-written destinations therefore add no user value and should not cause an
    otherwise grounded answer to be discarded.
    """

    value = MARKDOWN_LINK_PATTERN.sub(lambda match: match.group(1).strip(), answer)
    value = AUTOLINK_PATTERN.sub("相关来源", value)
    value = RAW_LINK_PATTERN.sub("相关来源", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def recover_provider_answer(
    answer: str,
    max_output_chars: int,
    *,
    allowed_dotted_terms: set[str],
) -> AnswerRecoveryResult:
    """Apply narrow, deterministic repairs before using an evidence fallback."""

    repaired = answer
    first_reason: str | None = None
    for _ in range(6):
        try:
            return AnswerRecoveryResult(
                answer=validate_provider_answer(
                    repaired,
                    max_output_chars,
                    allowed_dotted_terms=allowed_dotted_terms,
                ),
                strategy="unchanged" if first_reason is None else "references_to_cards",
                validation_reason=first_reason,
            )
        except ValueError as exc:
            reason = str(exc)
            first_reason = first_reason or reason
            if reason == "link":
                repaired = normalize_inline_links(repaired)
                continue
            if reason.startswith("domain:"):
                domain = reason.partition(":")[2]
                repaired = re.sub(
                    re.escape(domain),
                    "相关资料",
                    repaired,
                    flags=re.IGNORECASE,
                )
                continue
            raise
    raise ValueError(first_reason or "unrecoverable_reference")


def _plain_evidence_text(value: str | None, *, limit: int) -> str:
    text = CONTROL_CHARACTER_PATTERN.sub("", str(value or ""))
    text = MARKDOWN_LINK_PATTERN.sub(lambda match: match.group(1).strip(), text)
    text = AUTOLINK_PATTERN.sub("", text)
    text = RAW_LINK_PATTERN.sub("", text)
    text = HTML_TAG_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -—：:；;")
    return text[:limit]


def build_evidence_fallback(
    request: str,
    cards: list[AgentLinkCard],
) -> str:
    """Build a useful answer only from already-validated evidence projections.

    This is the last recovery tier. It performs no new search and makes no product
    claims beyond card titles, descriptions and reasons already returned by domain
    services.
    """

    if not cards:
        return (
            "这次回答暂时没有取得足够的可验证内容。你可以保留当前问题稍后重试，"
            "或补充希望学习的主题、要完成的任务和偏好，我会据此重新整理。"
        )

    grouped: dict[str, list[AgentLinkCard]] = {
        "learning_node": [],
        "tool": [],
        "page": [],
        "web": [],
    }
    for card in cards[:12]:
        grouped[card.type].append(card)

    lines = ["我已根据本轮取得的可验证内容，先为你整理出可直接使用的结果。"]
    section_names = {
        "learning_node": "学习内容",
        "tool": "工具建议",
        "page": "站内入口",
        "web": "外部补充资料",
    }
    for source_type in ("learning_node", "tool", "page", "web"):
        items = grouped[source_type]
        if not items:
            continue
        lines.extend(("", f"{section_names[source_type]}："))
        for index, card in enumerate(items, start=1):
            title = _plain_evidence_text(card.title, limit=120) or f"候选 {index}"
            detail = _plain_evidence_text(card.description or card.reason, limit=260)
            lines.append(f"{index}. {title}" + (f"：{detail}" if detail else ""))

    normalized_request = str(request or "").lower()
    if grouped["learning_node"]:
        lines.extend((
            "",
            "建议的学习方式：先打开最匹配的学习内容建立整体认识，再按页面目录逐节推进；"
            "每完成一节就用自己的话复述关键概念，并做一个最小练习验证理解。",
        ))
        if grouped["tool"]:
            lines.append("完成基础学习后，再从工具建议中选择一个进行实践，避免只看资料不动手。")
    elif grouped["tool"]:
        lines.extend((
            "",
            "选择建议：先根据当前任务匹配描述最接近的候选，再核对免费范围、使用限制和实际可用性；"
            "先用一个小任务试用，确认合适后再投入完整流程。",
        ))
    elif grouped["page"]:
        lines.extend(("", "你可以从上面的站内入口继续，页面卡片中的地址已经过单独校验。"))

    if re.search(r"(?:生成|制作|画|设计).{0,10}(?:图片|海报|视频|配图)", normalized_request):
        lines.insert(
            1,
            "本站不能直接交付对应的媒体文件；上面的内容可作为选择外部工具或继续完善文本方案的依据。",
        )
    lines.extend(("", "如果你愿意补充目标、基础水平或使用偏好，我可以在这些内容上继续细化。"))
    return "\n".join(lines)


def validated_evidence_fallback(
    request: str,
    cards: list[AgentLinkCard],
    max_output_chars: int,
    *,
    allowed_dotted_terms: set[str],
) -> str:
    """Return a safe evidence answer even when a catalog field is malformed."""

    candidate = build_evidence_fallback(request, cards)
    try:
        return validate_provider_answer(
            candidate,
            max_output_chars,
            allowed_dotted_terms=allowed_dotted_terms,
        )
    except ValueError:
        # Do not interpolate evidence into the final emergency sentence. Domain
        # services remain observable through cards, while unsafe catalog text is
        # prevented from crossing into prose.
        safe = (
            f"本轮已取得 {len(cards)} 项可验证内容，但其中部分文字无法安全展示。"
            "你仍可使用下方经过单独校验的入口继续查看，或稍后重新生成回答。"
            if cards
            else "这次回答暂时没有取得足够的可验证内容，请稍后重试或补充更具体的目标。"
        )
        return validate_provider_answer(safe, max_output_chars)
