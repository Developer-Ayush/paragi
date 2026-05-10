"""
graph/edge.py — The High-Fidelity Edge domain object.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, List
from core.enums import EdgeType
from core.constants import (
    VECTOR_SIZE, ETA_DEFAULT, ALPHA_DEFAULT, BETA_DEFAULT, 
    EDGE_STRENGTH_FLOOR, EDGE_STRENGTH_MAX
)


class Edge:
    """
    A high-fidelity cognitive edge.
    
    Implements §5.3 of the Paragi paper:
    Δstrength = η(S - strength) + αR - βD
    """

    def __init__(
        self,
        source: str,
        target: str,
        edge_type: EdgeType,
        weight: float = 0.1,
        confidence: float = 1.0,
        vector: Optional[List[float]] = None,
        emotional_weight: float = 0.0,
        stability: float = 1.0,
        decay_param: float = 1.0,
        temporal_data: Dict[str, Any] = None,
        causal_strength: float = 0.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        self.source = source
        self.target = target
        self.edge_type = edge_type
        self.weight = weight # synonymous with 'strength' in the paper
        self.confidence = confidence
        
        # High-Fidelity Fields
        self.vector = vector or [0.0] * VECTOR_SIZE
        self.emotional_weight = emotional_weight
        self.stability = stability
        self.decay_param = decay_param
        
        self.temporal_data = temporal_data or {}
        self.causal_strength = causal_strength
        self.metadata = metadata or {}
        
        self.created_at = time.time()
        self.last_activated = self.created_at
        self.recall_count = 0

    def reinforce(
        self, 
        s_score: Optional[float] = None, 
        eta: float = ETA_DEFAULT, 
        alpha: float = ALPHA_DEFAULT, 
        beta: float = BETA_DEFAULT
    ) -> None:
        """
        Advanced Hebbian reinforcement formula:
        Δstrength = η(S - strength) + αR - βD
        """
        self.recall_count += 1
        self.last_activated = time.time()
        
        # S (target strength) defaults to emotional_weight or 1.0
        S = s_score if s_score is not None else max(self.emotional_weight, 0.8)
        
        # Formula implementation
        delta = eta * (S - self.weight) + (alpha * self.recall_count) - (beta * self.decay_param)
        
        self.weight = max(EDGE_STRENGTH_FLOOR, min(EDGE_STRENGTH_MAX, self.weight + delta))

    def decay(self, base_rate: float = 0.01) -> None:
        """Temporal decay of edge weight and vector."""
        # Scalar weight decay
        self.weight = max(EDGE_STRENGTH_FLOOR, self.weight * (1.0 - base_rate))
        
        # Vector decay (simplified for now, specific logic in vector_decay.py)
        for i in range(len(self.vector)):
            self.vector[i] *= (1.0 - base_rate)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "confidence": self.confidence,
            "vector": self.vector,
            "emotional_weight": self.emotional_weight,
            "stability": self.stability,
            "decay_param": self.decay_param,
            "temporal_data": self.temporal_data,
            "causal_strength": self.causal_strength,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_activated": self.last_activated,
            "recall_count": self.recall_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Edge:
        created_at = data.pop("created_at", time.time())
        last_activated = data.pop("last_activated", created_at)
        recall_count = data.pop("recall_count", 0)
        edge = cls(**data)
        edge.created_at = created_at
        edge.last_activated = last_activated
        edge.recall_count = recall_count
        return edge
