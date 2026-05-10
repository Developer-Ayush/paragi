"""
graph/node.py — The Node domain object.

Represents a localized atomic concept within the graph space.
Nodes encapsulate their own temporal decay and activation logic.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from core.enums import NodeType


class Node:
    """
    A cognitive node (concept) within the graph.
    
    Architectural Role:
    The fundamental atomic unit of intelligence. Nodes represent concepts,
    entities, or abstract ideas. Their meaning is refined by their connections.
    """

    def __init__(
        self,
        id: str,
        label: str,
        type: NodeType = NodeType.CONCEPT,
        embedding: List[float] = None,
        activation: float = 0.0,
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        self.id = id
        self.label = label
        self.type = type
        self.embedding = embedding or []
        self.activation = activation
        self.confidence = confidence
        self.metadata = metadata or {}
        
        # Internal state for decay and tracking
        self.last_accessed = time.time()
        self.access_count = 0

    def record_access(self) -> None:
        """Called whenever the traversal engine touches this node."""
        self.access_count += 1
        self.last_accessed = time.time()

    def set_activation(self, level: float) -> None:
        """Inject spreading activation energy into this concept."""
        self.activation = max(0.0, min(1.0, level))

    def compute_salience(self, current_time: float, decay_hours: float = 24.0) -> float:
        """
        Calculates how salient (top-of-mind) this concept is right now.
        Uses exponential time decay based on last access.
        """
        age_hours = (current_time - self.last_accessed) / 3600.0
        if age_hours <= 0:
            return 1.0
        decay_factor = 0.5 ** (age_hours / decay_hours)
        return self.activation * decay_factor

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence or API."""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "embedding": self.embedding,
            "activation": self.activation,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Node:
        """Create Node instance from dict."""
        last_accessed = data.pop("last_accessed", time.time())
        access_count = data.pop("access_count", 0)
        node = cls(**data)
        node.last_accessed = last_accessed
        node.access_count = access_count
        return node
