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
class Relation:
    """A directed semantic relation between two concepts."""
    source: str
    relation: str          # EdgeType value: CAUSES, TEMPORAL, ANALOGY, etc.
    target: str
    confidence: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalData:
    """Temporal information extracted from the query."""
    is_temporal: bool = False
    temporal_nature: str = "static"        # static | realtime | episodic
    time_references: List[str] = field(default_factory=list)
    sequence_order: List[str] = field(default_factory=list)


@dataclass
class SemanticIR:
    """
    Universal Semantic Intermediate Representation.

    Every query, fact, and reasoning result flows through this structure.
    The encoder produces it from human language.
    The graph builder reads it to update the graph.
    The reasoning router uses it to select reasoners.
    The decoder converts reasoning results back to language.
    """

    # ── Intent ──────────────────────────────────────────────────────────
    intent: str                            # e.g. causal_question, concept_query, fact_assertion
    reasoning_mode: str                    # causal | temporal | analogy | abstraction | general

    # ── Semantic content ─────────────────────────────────────────────────
    entities: List[str] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)

    # ── Context ───────────────────────────────────────────────────────────
    context: Dict[str, Any] = field(default_factory=dict)

    # ── Confidence and quality ────────────────────────────────────────────
    confidence: float = 0.5
    learnability: float = 0.0              # 0=question, 1=definitive fact

    # ── Temporal information ──────────────────────────────────────────────
    temporal_data: TemporalData = field(default_factory=TemporalData)

    # ── Graph targeting ──────────────────────────────────────────────────
    analogy_targets: List[str] = field(default_factory=list)
    activation_targets: List[str] = field(default_factory=list)

    # ── Metadata ──────────────────────────────────────────────────────────
    raw_text: str = ""
    normalized_text: str = ""
    source_concept: Optional[str] = None   # primary source entity (for relations)
    target_concept: Optional[str] = None   # primary target entity (for relations)
    personal_attribute: Optional[str] = None
    personal_value: Optional[str] = None
    semantic_vector: List[float] = field(default_factory=list)  # 700-dim embedding
    query_type: str = "STATIC_KNOWLEDGE"
    emotional_tone: str = "neutral"
    requires_web: bool = False
    requires_graph: bool = True
    requires_personal_graph: bool = False
    rewrite_applied: bool = False
    graph_edges: List[Dict[str, Any]] = field(default_factory=list)  # LLM-extracted edges

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "intent": self.intent,
            "reasoning_mode": self.reasoning_mode,
            "entities": self.entities,
            "relations": [
                {
                    "source": r.source,
                    "relation": r.relation,
                    "target": r.target,
                    "confidence": r.confidence,
                }
                for r in self.relations
            ],
            "constraints": self.constraints,
            "context": self.context,
            "confidence": self.confidence,
            "learnability": self.learnability,
            "temporal_data": {
                "is_temporal": self.temporal_data.is_temporal,
                "temporal_nature": self.temporal_data.temporal_nature,
                "time_references": self.temporal_data.time_references,
                "sequence_order": self.temporal_data.sequence_order,
            },
            "analogy_targets": self.analogy_targets,
            "activation_targets": self.activation_targets,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "source_concept": self.source_concept,
            "target_concept": self.target_concept,
            "query_type": self.query_type,
            "emotional_tone": self.emotional_tone,
        }