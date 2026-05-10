"""graph/node.py — The Node domain object.

Represents a localized atomic concept within the graph space.
Nodes encapsulate their own temporal decay and activation logic.
"""
from __future__ import annotations

import time
from .schemas import NodeSchema


class Node:
    """
    A cognitive node (concept) within the graph.
    
    Architectural Role:
    The fundamental atomic unit of intelligence. Nodes don't hold complex meaning 
    themselves—meaning emerges from their edge topography. Nodes only track their 
    salience (how important they are right now) and abstraction tier.
    """

    def __init__(self, schema: NodeSchema) -> None:
        self._data = schema

    @classmethod
    def create(cls, node_id: str, label: str, *, abstraction_level: int = 0) -> "Node":
        """Factory for new nodes."""
        ts = time.time()
        return cls(NodeSchema(
            id=node_id,
            label=label,
            created=ts,
            last_accessed=ts,
            access_count=1,
            activation_level=0.0,
            abstraction_level=abstraction_level
        ))

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def id(self) -> str: return self._data.id

    @property
    def label(self) -> str: return self._data.label

    @property
    def access_count(self) -> int: return self._data.access_count

    @property
    def activation_level(self) -> float: return self._data.activation_level

    # ── Domain Logic ────────────────────────────────────────────────────────

    def record_access(self) -> None:
        """Called whenever the traversal engine touches this node."""
        self._data.access_count += 1
        self._data.last_accessed = time.time()

    def set_activation(self, level: float) -> None:
        """Inject spreading activation energy into this concept."""
        self._data.activation_level = max(0.0, min(1.0, level))

    def compute_salience(self, current_time: float, decay_hours: float = 24.0) -> float:
        """
        Calculates how salient (top-of-mind) this concept is right now.
        Uses exponential time decay based on last access.
        """
        age_hours = (current_time - self._data.last_accessed) / 3600.0
        if age_hours <= 0:
            return 1.0
        decay_factor = 0.5 ** (age_hours / decay_hours)
        return self._data.activation_level * decay_factor

    def to_schema(self) -> NodeSchema:
        """Export to clean data layer."""
        return self._data.model_copy()
