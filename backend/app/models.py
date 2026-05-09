from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import List


class EdgeType(str, Enum):
    CAUSES = "CAUSES"
    CORRELATES = "CORRELATES"
    IS_A = "IS_A"
    TEMPORAL = "TEMPORAL"
    INFERRED = "INFERRED"


class QueryType(str, Enum):
    """Phase 1 — query classification categories."""
    STATIC_KNOWLEDGE = "STATIC_KNOWLEDGE"
    REALTIME_KNOWLEDGE = "REALTIME_KNOWLEDGE"
    PERSONAL_MEMORY = "PERSONAL_MEMORY"
    EPISODIC_MEMORY = "EPISODIC_MEMORY"
    CAUSAL_REASONING = "CAUSAL_REASONING"
    ANALOGICAL_REASONING = "ANALOGICAL_REASONING"
    EXPLORATORY_REASONING = "EXPLORATORY_REASONING"


@dataclass(slots=True)
class NodeRecord:
    id: str
    label: str
    created: float
    last_accessed: float
    access_count: int


@dataclass(slots=True)
class EdgeRecord:
    id: str
    source: str
    target: str
    type: EdgeType
    vector: List[float]
    strength: float
    emotional_weight: float
    recall_count: int
    stability: float
    last_activated: float
    created: float
    confidence: float


# ── Lightweight suffix stemmer (no external deps) ──────────────────────
# Covers ~90% of common English inflections: plurals, verb forms, -ing, -ed, -ly

_STEM_RULES: list[tuple[re.Pattern, str, int]] = [
    # Order matters — more specific patterns first
    (re.compile(r"ies$"), "y", 3),        # flies → fly, cities → city
    (re.compile(r"sses$"), "ss", 4),      # masses → mass
    (re.compile(r"ness$"), "", 4),         # happiness → happi (close enough)
    (re.compile(r"ying$"), "y", 4),        # flying → fly
    (re.compile(r"([^aeiou])ing$"), r"\1", 4),  # burning → burn, running → run
    (re.compile(r"([aeiou][^aeiou])ing$"), r"\1e", 4),  # making → make
    (re.compile(r"ting$"), "t", 4),        # cutting → cut
    (re.compile(r"([^aeiou])ed$"), r"\1", 3),   # burned → burn
    (re.compile(r"ied$"), "y", 3),         # cried → cry
    (re.compile(r"([aeiou][^aeiou])ed$"), r"\1e", 3),  # baked → bake
    (re.compile(r"([^s])s$"), r"\1", 2),   # cats → cat, burns → burn (but not 'ss')
]

# Words that should not be stemmed (too short or irregular)
_STEM_EXCEPTIONS = frozenset({
    "is", "was", "has", "his", "its", "this", "us", "yes", "no",
    "as", "does", "goes", "the", "news", "bus", "gas", "plus",
})


def stem_word(word: str) -> str:
    """Apply lightweight suffix stemming to a single word."""
    if len(word) <= 3 or word in _STEM_EXCEPTIONS:
        return word
    for pattern, replacement, min_len in _STEM_RULES:
        if len(word) >= min_len:
            result = pattern.sub(replacement, word)
            if result != word and len(result) >= 2:
                return result
    return word


def normalize_label(label: str) -> str:
    words = label.strip().lower().split()
    stemmed = [stem_word(w) for w in words]
    return " ".join(stemmed)


def normalize_label_raw(label: str) -> str:
    """Normalize without stemming — for display purposes."""
    return " ".join(label.strip().lower().split())


def make_node_id(label: str) -> str:
    normalized = normalize_label(label)
    return hashlib.blake2s(normalized.encode("utf-8"), digest_size=16).hexdigest()


def make_edge_id(source_id: str, target_id: str) -> str:
    raw = f"{source_id}->{target_id}".encode("utf-8")
    return hashlib.blake2s(raw, digest_size=16).hexdigest()


def now_ts() -> float:
    return time.time()

