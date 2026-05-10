"""
core/semantic_ir.py — Universal Semantic Intermediate Representation

Every piece of information flowing through the Paragi cognitive runtime
is represented as a SemanticIR. This is the universal interchange format
between the encoder, graph, reasoning engine, and decoder.

Pipeline:
    Human Language → SemanticIR → Graph → Reasoning → SemanticIR → Language
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IRNode:
    """A node representation within the IR."""
    label: str
    type: str = "concept"
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class IREdge:
    """A raw edge representation within the IR."""
    source: str
    target: str
    relation: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IRRelation:
    """A semantic relation extracted from text."""
    source: str
    relation: str          # EdgeType value: CAUSES, TEMPORAL, ANALOGY, etc.
    target: str
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticIR:
    """
    Universal Semantic Intermediate Representation.
    
    The source of truth for a single 'thought' or 'input' as it moves 
    through the cognitive pipeline.
    """

    # ── Core Content ───────────────────────────────────────────────────
    text: str = ""                         # raw input text
    tokens: List[str] = field(default_factory=list)
    
    # ── Semantic Extraction ────────────────────────────────────────────
    entities: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)
    relations: List[IRRelation] = field(default_factory=list)
    
    # ── Intent & Reasoning ─────────────────────────────────────────────
    intent: str = "general_query"
    confidence: float = 0.0
    
    # ── Specialized Markers ───────────────────────────────────────────
    temporal_markers: List[Dict[str, Any]] = field(default_factory=list)
    causal_markers: List[Dict[str, Any]] = field(default_factory=list)
    ambiguities: List[Dict[str, Any]] = field(default_factory=list)
    
    # ── Metadata & Context ────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "text": self.text,
            "tokens": self.tokens,
            "entities": self.entities,
            "concepts": self.concepts,
            "relations": [
                {
                    "source": r.source,
                    "relation": r.relation,
                    "target": r.target,
                    "confidence": r.confidence,
                    "attributes": r.attributes
                }
                for r in self.relations
            ],
            "intent": self.intent,
            "confidence": self.confidence,
            "temporal_markers": self.temporal_markers,
            "causal_markers": self.causal_markers,
            "ambiguities": self.ambiguities,
            "metadata": self.metadata,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticIR:
        """Create a SemanticIR instance from a dictionary."""
        relations_data = data.pop("relations", [])
        relations = [IRRelation(**r) for r in relations_data]
        return cls(relations=relations, **data)