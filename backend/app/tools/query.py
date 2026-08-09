from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCapabilityTaxon:
    id: str
    activation_pattern: re.Pattern[str]
    search_terms: tuple[str, ...]
    evidence_terms: tuple[str, ...]

    def is_active(self, value: str) -> bool:
        return bool(self.activation_pattern.search(value))


@dataclass(frozen=True)
class NormalizedTaskQuery:
    raw: str
    focused_text: str
    generic_terms: tuple[str, ...]
    capabilities: tuple[ToolCapabilityTaxon, ...]

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(capability.id for capability in self.capabilities)

    @property
    def capability_search_terms(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                term
                for capability in self.capabilities
                for term in capability.search_terms
            )
        )


VISUAL_CREATION = ToolCapabilityTaxon(
    id="visual_creation",
    activation_pattern=re.compile(
        r"制图|绘图|画图|生图|文生图|图片|图像|海报|封面|插画|修图|抠图|视觉|小红书",
        re.I,
    ),
    search_terms=(
        "绘画",
        "图像",
        "设计",
        "修图",
        "排版",
        "文生图",
        "生图",
        "海报",
        "封面",
        "商品素材",
    ),
    evidence_terms=(
        "AI 绘画工具",
        "绘画",
        "图像",
        "设计",
        "修图",
        "排版",
        "文生图",
        "生图",
        "商品素材",
        "抠图",
    ),
)

CAPABILITY_TAXONOMY = (VISUAL_CREATION,)
GENERIC_TERMS = ("AI", "人工智能", "工具")
TASK_SCAFFOLDING = (
    "帮我找几个",
    "帮我找一些",
    "帮我找",
    "给我找",
    "制作一张",
    "生成一张",
    "设计一张",
    "推荐几个",
    "推荐一些",
    "推荐",
    "我想要",
    "我想",
    "我要",
    "帮我",
)


class TaskQueryNormalizer:
    """Extract task capability signals without owning catalog ranking rules."""

    def normalize(self, value: str | None) -> NormalizedTaskQuery:
        raw = re.sub(r"\s+", " ", str(value or "").strip())
        focused = raw
        for phrase in sorted(TASK_SCAFFOLDING, key=len, reverse=True):
            focused = focused.replace(phrase, " ")

        generic_terms = tuple(
            term
            for term in GENERIC_TERMS
            if re.search(re.escape(term), raw, re.I)
        )
        focused = re.sub(r"(?i)(?<![a-z0-9])AI(?![a-z0-9])", " ", focused)
        focused = focused.replace("人工智能", " ").replace("工具", " ")
        focused = re.sub(r"[，。！？；：、,.!?;:]+", " ", focused)
        focused = re.sub(r"\s+", " ", focused).strip()

        compact_raw = re.sub(r"\s+", "", raw.lower())
        capabilities = tuple(
            capability
            for capability in CAPABILITY_TAXONOMY
            if capability.is_active(compact_raw)
        )
        return NormalizedTaskQuery(
            raw=raw.lower(),
            focused_text=focused.lower(),
            generic_terms=generic_terms,
            capabilities=capabilities,
        )


TASK_QUERY_NORMALIZER = TaskQueryNormalizer()


def capability_matches(evidence: str, capability: ToolCapabilityTaxon) -> bool:
    compact_evidence = re.sub(r"\s+", "", evidence.lower())
    return any(
        re.sub(r"\s+", "", term.lower()) in compact_evidence
        for term in capability.evidence_terms
    )
