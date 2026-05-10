"""core/enums.py — Consolidated enumerations for the Paragi cognitive runtime."""
from __future__ import annotations

from enum import Enum


# ── Edge Types ─────────────────────────────────────────────────────────────────
class EdgeType(str, Enum):
    """All supported semantic edge types in the cognitive graph."""
    # Original types (preserved for backward compatibility)
    CAUSES = "CAUSES"
    CORRELATES = "CORRELATES"
    IS_A = "IS_A"
    TEMPORAL = "TEMPORAL"
    INFERRED = "INFERRED"

    # Extended cognitive types
    ANALOGY = "ANALOGY"          # structural graph similarity
    PART_OF = "PART_OF"          # compositional membership
    ABSTRACTS_TO = "ABSTRACTS_TO"  # abstraction hierarchy upward
    CONTRADICTS = "CONTRADICTS"  # logical contradiction
    DEPENDS_ON = "DEPENDS_ON"    # dependency / prerequisite
    GOAL = "GOAL"                # intentional goal structure
    SEQUENCE = "SEQUENCE"        # ordered sequence membership
    SIMILARITY = "SIMILARITY"    # semantic similarity (weaker than ANALOGY)
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    PRECONDITION = "PRECONDITION"
    RESULT_OF = "RESULT_OF"

    @classmethod
    def get(cls, name: str, default: EdgeType = ASSOCIATED_WITH) -> EdgeType:
        try:
            return cls[name.upper()]
        except (KeyError, AttributeError):
            return default


# ── Query Types ────────────────────────────────────────────────────────────────
class QueryType(str, Enum):
    """Classification of incoming queries for pipeline routing."""
    STATIC_KNOWLEDGE = "STATIC_KNOWLEDGE"
    REALTIME_KNOWLEDGE = "REALTIME_KNOWLEDGE"
    PERSONAL_MEMORY = "PERSONAL_MEMORY"
    EPISODIC_MEMORY = "EPISODIC_MEMORY"
    CAUSAL_REASONING = "CAUSAL_REASONING"
    ANALOGICAL_REASONING = "ANALOGICAL_REASONING"
    EXPLORATORY_REASONING = "EXPLORATORY_REASONING"
    TEMPORAL_REASONING = "TEMPORAL_REASONING"
    PLANNING = "PLANNING"
    CONTRADICTION = "CONTRADICTION"


# ── Reasoning Modes ────────────────────────────────────────────────────────────
class ReasoningMode(str, Enum):
    """Reasoning strategy selected by the router based on SemanticIR."""
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    ANALOGY = "analogy"
    ABSTRACTION = "abstraction"
    PREDICTIVE = "predictive"
    CONTRADICTION = "contradiction"
    PLANNING = "planning"
    PROBABILISTIC = "probabilistic"
    GENERAL = "general"


# ── Memory Types ───────────────────────────────────────────────────────────────
class MemoryType(str, Enum):
    """Types of memory in the cognitive architecture."""
    SEMANTIC = "semantic"    # permanent graph knowledge
    EPISODIC = "episodic"    # time-decaying personal experiences
    WORKING = "working"      # active context window (current query)
    REALTIME = "realtime"    # never persisted, TTL-bound


# ── Node Types ─────────────────────────────────────────────────────────────────
class NodeType(str, Enum):
    """Semantic categories for graph nodes."""
    CONCEPT = "concept"          # general knowledge concept
    ENTITY = "entity"            # named entity (person, place, thing)
    ABSTRACT = "abstract"        # abstract idea or category
    TEMPORAL = "temporal"        # time reference
    SELF = "self"                # user self-reference
    GOAL = "goal"                # intentional goal
    EVENT = "event"              # event or action


# ── Activation States ──────────────────────────────────────────────────────────
class ActivationState(str, Enum):
    """Activation state of graph nodes during a reasoning pass."""
    INACTIVE = "inactive"
    PRIMED = "primed"       # in neighborhood of query
    ACTIVE = "active"       # directly traversed
    FOCAL = "focal"         # highest salience in current query
    DECAYING = "decaying"   # recently active, now fading
