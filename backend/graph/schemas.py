"""
graph/schemas.py — Pydantic schemas for the Cognitive Graph.

These schemas are used for serialization and API boundaries.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core.enums import EdgeType, NodeType


class NodeSchema(BaseModel):
    """Data definition for a concept in the cognitive graph."""
    id: str
    label: str
    type: NodeType = NodeType.CONCEPT
    embedding: List[float] = Field(default_factory=list)
    activation: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_accessed: float
    access_count: int


class EdgeSchema(BaseModel):
    """Data definition for a semantic relation in the cognitive graph."""
    source: str
    target: str
    edge_type: EdgeType
    weight: float = 0.1
    confidence: float = 1.0
    temporal_data: Dict[str, Any] = Field(default_factory=dict)
    causal_strength: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float
    last_activated: float
    recall_count: int


class GraphSchema(BaseModel):
    """Schema for a full subgraph or state export."""
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]
