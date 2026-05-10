"""graph/edge.py — The Edge domain object.

Represents a typed semantic relation between two nodes.
Edges encapsulate reinforcement learning logic (Hebbian updates) and temporal decay.
"""
from __future__ import annotations

import time
from typing import List

from core.enums import EdgeType
from .schemas import EdgeSchema


class Edge:
    """
    A cognitive edge (relation) within the graph.
    
    Architectural Role:
    The actual 'intelligence' of the system. Edges represent causal, temporal, 
    and analogical synapses. They are active entities that strengthen with use 
    (Hebbian learning) and wither without it (Temporal decay).
    """

    def __init__(self, schema: EdgeSchema) -> None:
        self._data = schema

    @classmethod
    def create(
        cls, edge_id: str, source: str, target: str, edge_type: EdgeType,
        *, strength: float = 0.1, confidence: float = 0.5, vector: List[float] | None = None
    ) -> "Edge":
        ts = time.time()
        return cls(EdgeSchema(
            id=edge_id, source=source, target=target, type=edge_type,
            strength=strength, confidence=confidence, vector=vector or [],
            stability=1.0, emotional_weight=0.0,
            recall_count=0, last_activated=ts, created=ts
        ))

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def id(self) -> str: return self._data.id

    @property
    def source(self) -> str: return self._data.source

    @property
    def target(self) -> str: return self._data.target

    @property
    def type(self) -> EdgeType: return self._data.type

    @property
    def strength(self) -> float: return self._data.strength

    # ── Domain Logic: Hebbian Learning ──────────────────────────────────────

    def reinforce(self, eta: float = 0.05, alpha: float = 0.001) -> None:
        """
        Hebbian reinforcement. 
        Increases synaptic strength when successfully traversed for reasoning.
        """
        self._data.recall_count += 1
        self._data.last_activated = time.time()
        
        # Rule: ΔS = η * (Target_S - Current_S) + (α * recall)
        # Using emotional_weight as a modifier if present, else pushing toward 1.0
        target_s = max(0.5, self._data.emotional_weight) if self._data.emotional_weight > 0 else 1.0
        
        delta = eta * (target_s - self._data.strength) + (alpha * self._data.recall_count)
        self._data.strength = min(1.0, self._data.strength + delta)

    def weaken(self, penalty: float = 0.1) -> None:
        """
        Explicit penalty (e.g., when contradicted by new information).
        """
        self._data.strength = max(0.01, self._data.strength - penalty)

    def decay(self, base_rate: float, floor: float = 0.01) -> None:
        """
        Temporal decay. Weakens connections that are not used.
        """
        # Stability parameter provides resistance to decay
        actual_rate = base_rate * (1.0 / max(0.1, self._data.stability))
        self._data.strength = floor + (self._data.strength - floor) * (1.0 - actual_rate)

    def to_schema(self) -> EdgeSchema:
        return self._data.model_copy()
