from __future__ import annotations

import re
from dataclasses import dataclass


VALID_SCOPES = {"auto", "main", "personal"}

_PERSONAL_PATTERNS = [
    re.compile(r"\bmy name is\b"),
    re.compile(r"\bwhat is my name\b"),
    re.compile(r"\bmy nationality is\b"),
    re.compile(r"\bwhat is my nationality\b"),
    re.compile(r"\bi am\b"),
    re.compile(r"\bi'm\b"),
    re.compile(r"\bi am from\b"),
    re.compile(r"\bwhere am i from\b"),
    re.compile(r"\bwho am i\b"),
    re.compile(r"\bi live in\b"),
    re.compile(r"\bwhere do i live\b"),
    re.compile(r"\bi work at\b"),
    re.compile(r"\bwhere do i work\b"),
    re.compile(r"\bwhat is my identity\b"),
    re.compile(r"\bwhat do i like\b"),
    re.compile(r"\bmy email\b"),
    re.compile(r"\bmy phone\b"),
    re.compile(r"\bmy address\b"),
    re.compile(r"\bmy birthday\b"),
    re.compile(r"\bmy age\b"),
    re.compile(r"\bmy favorite\b"),
    re.compile(r"\bmy\s+[a-z0-9_ ]+\s+is\b"),
    re.compile(r"\bwhat is my\s+[a-z0-9_ ]+\b"),
]

_PERSONAL_BENEFIT_PATTERNS = [
    re.compile(r"\bmy nationality is\b"),
    re.compile(r"\bwhat is my nationality\b"),
    re.compile(r"\bi am from\b"),
    re.compile(r"\bwhere am i from\b"),
]


@dataclass(frozen=True, slots=True)
class ScopeDecision:
    requested_scope: str
    selected_scope: str
    reason: str
    benefits_main_graph: bool


def decide_scope(text: str, requested_scope: str) -> ScopeDecision:
    clean_scope = (requested_scope or "auto").strip().lower()
    if clean_scope not in VALID_SCOPES:
        clean_scope = "auto"

    lower_text = (text or "").strip().lower()
    personal_signal = is_personal_profile_input(lower_text)
    personal_benefit_signal = is_personal_profile_that_benefits_main(lower_text)

    if clean_scope == "personal":
        return ScopeDecision(
            requested_scope=clean_scope,
            selected_scope="personal",
            reason="forced_personal",
            benefits_main_graph=personal_benefit_signal,
        )

    if clean_scope == "main":
        if personal_signal:
            return ScopeDecision(
                requested_scope=clean_scope,
                selected_scope="personal",
                reason="protected_personal_profile",
                benefits_main_graph=personal_benefit_signal,
            )
        return ScopeDecision(
            requested_scope=clean_scope,
            selected_scope="main",
            reason="forced_main",
            benefits_main_graph=True,
        )

    if personal_signal:
        return ScopeDecision(
            requested_scope=clean_scope,
            selected_scope="personal",
            reason="auto_personal_profile",
            benefits_main_graph=personal_benefit_signal,
        )

    return ScopeDecision(
        requested_scope=clean_scope,
        selected_scope="main",
        reason="auto_world_knowledge",
        benefits_main_graph=True,
    )


def is_personal_profile_input(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return False
    for pattern in _PERSONAL_PATTERNS:
        if pattern.search(normalized):
            return True
    return False


def is_personal_profile_that_benefits_main(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return False
    for pattern in _PERSONAL_BENEFIT_PATTERNS:
        if pattern.search(normalized):
            return True
    return False
