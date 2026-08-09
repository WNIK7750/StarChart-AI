from __future__ import annotations

import re
from typing import Any


LATIN_TERM = re.compile(r"[a-z0-9][a-z0-9.+#_-]{1,}", re.IGNORECASE)
CJK_RUN = re.compile(r"[\u3400-\u9fff]{2,}")

# These phrases describe the request rather than the subject. Removing them
# before CJK n-gram expansion keeps recall broad without ranking every course
# for generic wording such as "学习内容" or "请推荐".
QUERY_STOP_PHRASES = (
    "请你", "请帮", "帮我", "根据", "站内", "现有", "内容", "学习", "课程",
    "推荐", "适合", "用户", "想要", "一个", "第一个", "从零", "路线", "计划",
    "工具", "说明", "原因", "给出", "完成", "进行", "以及", "并且",
)


def recall_terms(query: str) -> list[str]:
    """Return deterministic high-recall terms for mixed Chinese/Latin input.

    The station corpus is intentionally small, so recall is preferred over
    aggressive query classification. Latin identifiers are kept intact while
    Chinese subject phrases are expanded to overlapping 2-4 character grams.
    """
    normalized = " ".join(str(query or "").lower().split())
    terms: list[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if len(value) >= 2 and value not in terms:
            terms.append(value)

    for match in LATIN_TERM.finditer(normalized):
        add(match.group(0))

    for raw_run in CJK_RUN.findall(normalized):
        runs = [raw_run]
        for phrase in QUERY_STOP_PHRASES:
            runs = [part for run in runs for part in run.split(phrase) if part]
        for run in runs:
            if len(run) <= 4:
                add(run)
            for width in (4, 3, 2):
                if len(run) < width:
                    continue
                for index in range(len(run) - width + 1):
                    add(run[index:index + width])
    return terms[:32]


def rank_learning_rows(
    rows: list[dict[str, Any]],
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    normalized = " ".join(str(query or "").lower().split())
    terms = recall_terms(normalized)
    if not normalized:
        return [dict(row) for row in rows[:limit]]

    field_weights = {
        "slug": 18,
        "title": 18,
        "subtitle": 8,
        "tagsText": 12,
        "materialTitle": 10,
        "materialDescription": 6,
        "materialOverview": 4,
        "sectionText": 5,
        "resourceText": 5,
        "catalogResourceText": 4,
        "provider": 3,
    }
    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for order, raw_row in enumerate(rows):
        row = dict(raw_row)
        matched_terms: list[str] = []
        matched_fields: list[str] = []
        score = 0
        title = str(row.get("title") or "").lower()
        slug = str(row.get("slug") or "").lower()
        if normalized in {title, slug}:
            score += 200
        elif normalized and (normalized in title or normalized in slug):
            score += 100
        for term in terms:
            term_matched = False
            for field, weight in field_weights.items():
                value = str(row.get(field) or "").lower()
                if term not in value:
                    continue
                term_matched = True
                score += weight
                if field not in matched_fields:
                    matched_fields.append(field)
            if term_matched:
                matched_terms.append(term)
        if not matched_terms and score == 0:
            continue
        row["matchedTerms"] = matched_terms
        row["matchedFields"] = matched_fields
        row["recallScore"] = score
        ranked.append((score, order, row))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in ranked[:limit]]
