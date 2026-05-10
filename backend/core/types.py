"""core/types.py — Shared type aliases and base data records."""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import List

# ── Primitive aliases ──────────────────────────────────────────────────────────
NodeID = str        # blake2s hex of normalized label
EdgeID = str        # blake2s hex of "source_id->target_id"
Vector = List[float]
SemanticVector = List[float]  # 700-dim cognitive embedding

VECTOR_SIZE = 1024   # stored edge vector size
SEMANTIC_DIMS = 700  # encoder output dimensions


# ── Core records ───────────────────────────────────────────────────────────────
@dataclass(slots=True)
class NodeRecord:
    """A single node in the cognitive graph."""
    id: NodeID
    label: str
    created: float
    last_accessed: float
    access_count: int


@dataclass(slots=True)
class EdgeRecord:
    """A directed weighted edge in the cognitive graph."""
    id: EdgeID
    source: NodeID
    target: NodeID
    type: str                  # EdgeType value
    vector: List[float]        # 1024-dim edge embedding
    strength: float            # 0.0–1.0
    emotional_weight: float    # emotional salience
    recall_count: int          # how many times strengthened
    stability: float           # resistance to decay
    last_activated: float
    created: float
    confidence: float          # epistemic confidence 0.0–1.0


# ── Utility functions ──────────────────────────────────────────────────────────
_normalize_re = re.compile(r"\s+")


def normalize_label(label: str) -> str:
    """Normalize a concept label: lowercase + collapse whitespace."""
    return _normalize_re.sub(" ", label.strip().lower())


def normalize_label_raw(label: str) -> str:
    """Normalize without lowercase — for display purposes."""
    return _normalize_re.sub(" ", label.strip())


def make_node_id(label: str) -> NodeID:
    normalized = normalize_label(label)
    return hashlib.blake2s(normalized.encode("utf-8"), digest_size=16).hexdigest()


def make_edge_id(source_id: NodeID, target_id: NodeID) -> EdgeID:
    raw = f"{source_id}->{target_id}".encode("utf-8")
    return hashlib.blake2s(raw, digest_size=16).hexdigest()


def now_ts() -> float:
    return time.time()
