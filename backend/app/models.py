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


def normalize_label(label: str) -> str:
    """Normalize label by lowercasing and collapsing whitespace. 
    Concept mapping is handled semantically by the encoder/LLM."""
    return " ".join(label.strip().lower().split())


def normalize_label_raw(label: str) -> str:
    """Normalize without lowercase — for display purposes."""
    return " ".join(label.strip().split())


def make_node_id(label: str) -> str:
    normalized = normalize_label(label)
    return hashlib.blake2s(normalized.encode("utf-8"), digest_size=16).hexdigest()


def make_edge_id(source_id: str, target_id: str) -> str:
    raw = f"{source_id}->{target_id}".encode("utf-8")
    return hashlib.blake2s(raw, digest_size=16).hexdigest()


def now_ts() -> float:
    return time.time()

