from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QueryModeDecision:
    mode: str
    reason: str
    disable_graph_learning: bool
    prefer_direct_llm: bool
    benefits_main_graph: bool


_REALTIME_PATTERNS = [
    re.compile(r"^\s*who\s+(is|was|are)\s+"),
    re.compile(r"^\s*what\s+is\s+the\s+(current|latest|today'?s|present)\b"),
    re.compile(r"\b(current|latest|today|now|live|breaking)\b"),
    re.compile(r"\b(news|headline|weather|forecast|temperature|rain)\b"),
    re.compile(r"\b(stock|share|price|market\s+cap|crypto|bitcoin|ethereum)\b"),
    re.compile(r"\b(score|match|fixture|result)\b"),
    re.compile(r"\b(prime minister|president|ceo|governor|minister)\b"),
    re.compile(r"\b(exchange rate|usd|inr|eur|gbp)\b"),
]


def decide_query_mode(text: str, *, is_personal_scope: bool) -> QueryModeDecision:
    normalized = (text or "").strip().lower()
    if not normalized:
        return QueryModeDecision(
            mode="standard",
            reason="empty_query",
            disable_graph_learning=False,
            prefer_direct_llm=False,
            benefits_main_graph=not is_personal_scope,
        )
    if is_personal_scope:
        return QueryModeDecision(
            mode="standard",
            reason="personal_scope",
            disable_graph_learning=False,
            prefer_direct_llm=False,
            benefits_main_graph=False,
        )

    for pattern in _REALTIME_PATTERNS:
        if pattern.search(normalized):
            return QueryModeDecision(
                mode="realtime",
                reason="realtime_pattern",
                disable_graph_learning=True,
                prefer_direct_llm=True,
                benefits_main_graph=False,
            )

    return QueryModeDecision(
        mode="standard",
        reason="default",
        disable_graph_learning=False,
        prefer_direct_llm=False,
        benefits_main_graph=True,
    )
