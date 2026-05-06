from __future__ import annotations

import hashlib
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


def normalize_label(label: str) -> str:
    return " ".join(label.strip().lower().split())


def make_node_id(label: str) -> str:
    normalized = normalize_label(label)
    return hashlib.blake2s(normalized.encode("utf-8"), digest_size=16).hexdigest()


def make_edge_id(source_id: str, target_id: str) -> str:
    raw = f"{source_id}->{target_id}".encode("utf-8")
    return hashlib.blake2s(raw, digest_size=16).hexdigest()


def now_ts() -> float:
    return time.time()

