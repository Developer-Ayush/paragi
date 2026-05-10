"""graph/schemas.py — Pydantic schemas for the Cognitive Graph.

These schemas strictly define the data bounds of our graph primitives.
They are used for serialization, API responses, and persistence boundaries,
keeping the internal object logic (in node.py/edge.py) clean.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field

from core.enums import EdgeType


class NodeSchema(BaseModel):
    """Data definition for a concept in the cognitive graph."""
    id: str = Field(..., description="Deterministic hash of the normalized label")
    label: str = Field(..., description="Canonical normalized text of the concept")
    created: float = Field(..., description="Timestamp of first creation")
    last_accessed: float = Field(..., description="Timestamp of last activation/traversal")
    access_count: int = Field(default=1, description="Number of times this node was hit")
    activation_level: float = Field(default=0.0, description="Current transient spreading activation level")
    abstraction_level: int = Field(default=0, description="0=concrete instance, higher=abstract category")


class EdgeSchema(BaseModel):
    """Data definition for a semantic relation in the cognitive graph."""
    id: str = Field(..., description="Deterministic hash of source + target")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: EdgeType = Field(..., description="The semantic nature of the relation")
    
    strength: float = Field(default=0.1, ge=0.0, le=1.0, description="Synaptic connection weight")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Epistemic certainty of this fact")
    stability: float = Field(default=1.0, description="Resistance to temporal decay")
    emotional_weight: float = Field(default=0.0, description="Limbic resonance parameter")
    
    recall_count: int = Field(default=0, description="Number of times this edge was successfully traversed")
    last_activated: float = Field(..., description="Timestamp of last traversal")
    created: float = Field(..., description="Timestamp of edge creation")
    
    vector: List[float] = Field(default_factory=list, description="Optional 700-dim semantic embedding mapping")
