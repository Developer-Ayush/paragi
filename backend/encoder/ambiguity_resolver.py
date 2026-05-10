"""encoder/ambiguity_resolver.py — Detect and resolve entity ambiguity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .concept_normalizer import normalize_concept


@dataclass
class AmbiguityResult:
    original: str
    resolved: str
    was_ambiguous: bool
    alternatives: List[str]
    confidence: float


# Simple disambiguation map for common ambiguous terms
_DISAMBIGUATION: Dict[str, Dict[str, str]] = {
    "bank": {
        "money": "bank_financial",
        "river": "river_bank",
        "default": "bank_financial",
    },
    "bat": {
        "animal": "bat_animal",
        "sport": "bat_cricket",
        "default": "bat",
    },
    "lead": {
        "metal": "lead_metal",
        "guide": "lead_guide",
        "default": "lead",
    },
}


def resolve(entity: str, context_tokens: List[str]) -> AmbiguityResult:
    """
    Resolve entity ambiguity using context tokens.
    Returns the most likely interpretation.
    """
    normalized = normalize_concept(entity)
    ctx_set = set(context_tokens)

    if normalized not in _DISAMBIGUATION:
        return AmbiguityResult(
            original=entity, resolved=normalized,
            was_ambiguous=False, alternatives=[], confidence=0.9,
        )

    sense_map = _DISAMBIGUATION[normalized]
    best_sense = sense_map.get("default", normalized)

    for context_word, sense in sense_map.items():
        if context_word == "default":
            continue
        if context_word in ctx_set:
            best_sense = sense
            break

    alternatives = [v for k, v in sense_map.items() if k != "default" and v != best_sense]
    return AmbiguityResult(
        original=entity, resolved=best_sense,
        was_ambiguous=True, alternatives=alternatives, confidence=0.75,
    )


def resolve_batch(entities: List[str], context_tokens: List[str]) -> List[str]:
    """Resolve all entities in a list, returning resolved forms."""
    return [resolve(e, context_tokens).resolved for e in entities]
