"""encoder/concept_normalizer.py — Normalize concepts to canonical graph forms."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from core.types import normalize_label

# Simple synonym map for concept canonicalization
_SYNONYMS: Dict[str, str] = {
    "burning": "burn",
    "burns": "burn",
    "burned": "burn",
    "heated": "heat",
    "heating": "heat",
    "hurts": "pain",
    "painful": "pain",
    "aches": "pain",
    "aching": "pain",
    "freezing": "cold",
    "frozen": "cold",
    "boiling": "heat",
    "smokes": "smoke",
    "smoking": "smoke",
    "steaming": "steam",
    "fires": "fire",
    "fires up": "fire",
    "ignites": "fire",
    "flames": "fire",
}

# Concept normalization: strip articles, possessives, plurals
_ARTICLE_RE = re.compile(r"^(a|an|the)\s+", re.IGNORECASE)
_POSSESSIVE_RE = re.compile(r"'s?\s*$")


def normalize_concept(text: str) -> str:
    """Normalize a concept string to canonical graph form."""
    t = normalize_label(text)
    # Strip leading articles
    t = _ARTICLE_RE.sub("", t).strip()
    # Strip possessives
    t = _POSSESSIVE_RE.sub("", t).strip()
    # Apply synonym map
    t = _SYNONYMS.get(t, t)
    return t


def normalize_concepts(items: List[str]) -> List[str]:
    """Normalize a list of concepts, removing duplicates."""
    seen = set()
    result = []
    for item in items:
        norm = normalize_concept(item)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def get_canonical(concept: str) -> Optional[str]:
    """Return canonical form of a concept, or None if it normalizes to empty."""
    result = normalize_concept(concept)
    return result if result else None
