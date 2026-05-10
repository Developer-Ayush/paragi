"""core/constants.py — System-wide constants for the Paragi cognitive runtime."""
from __future__ import annotations

# ── Vector dimensions (§3.2 of the Paragi paper) ──────────────────────────────
VECTOR_SIZE = 1024       # stored edge vector length
SEMANTIC_DIMS = 700      # encoder semantic output dimensions

# Named ranges within the 700-dim semantic vector
RANGE_DECISION_FATIGUE   = (0, 29)
RANGE_VISCERAL_STATES    = (30, 69)
RANGE_EMOTIONAL_RANGE    = (175, 209)
RANGE_PSYCHOLOGICAL_BLOCK = (210, 249)
RANGE_GENERAL_SEMANTIC   = (70, 174)   # primary hash embedding zone
RANGE_SEMANTIC_BRIDGE    = (250, 579)  # fastembed bridge zone
RANGE_INTELLECTUAL       = (480, 579)
RANGE_SITUATIONAL        = (380, 479)
RANGE_SOCIAL             = (280, 379)
RANGE_FACTUAL_WORLD      = (580, 639)
RANGE_CAUSAL_RELATIONAL  = (640, 669)
RANGE_OVERFLOW           = (670, 699)

# Domain anchor dimensions (within RANGE_FACTUAL_WORLD)
DOMAIN_ANCHOR_DIMS: dict[str, int] = {
    "general":    582,
    "medical":    596,
    "legal":      607,
    "physics":    618,
    "finance":    629,
    "technology": 638,
}

# ── Edge strength parameters ───────────────────────────────────────────────────
EDGE_STRENGTH_FLOOR    = 0.001
EDGE_DECAY_PER_CYCLE   = 0.005
EDGE_PRUNE_THRESHOLD   = 0.005
EDGE_STRENGTH_MAX      = 1.0

# Learning rate for edge strengthening (§5.3 update rule)
ETA_DEFAULT            = 0.1
ALPHA_DEFAULT          = 0.01   # recall bonus coefficient
BETA_DEFAULT           = 0.005  # decay penalty coefficient

# ── Confidence thresholds ──────────────────────────────────────────────────────
CONFIDENCE_HIGH        = 0.65
CONFIDENCE_MEDIUM      = 0.35
CONFIDENCE_LOW         = 0.12
LEARNING_THRESHOLD     = 0.5

# ── Traversal defaults ─────────────────────────────────────────────────────────
DEFAULT_MAX_HOPS       = 7
DEFAULT_MAX_PATHS      = 64
ANALOGY_MIN_SHARED     = 2
HUB_MIN_DEGREE         = 2

# ── Memory TTLs ────────────────────────────────────────────────────────────────
REALTIME_TTL_SECONDS   = 3600.0    # 1 hour
EPISODIC_DECAY_HOURS   = 24.0      # half-life

# ── Edge type relation text (for decoder) ──────────────────────────────────────
EDGE_RELATION_TEXT: dict[str, str] = {
    "CAUSES":       "causes",
    "CORRELATES":   "is associated with",
    "IS_A":         "is a type of",
    "TEMPORAL":     "usually happens before",
    "INFERRED":     "is likely related to",
    "ANALOGY":      "is analogous to",
    "PART_OF":      "is part of",
    "ABSTRACTS_TO": "is an abstraction of",
    "CONTRADICTS":  "contradicts",
    "DEPENDS_ON":   "depends on",
    "GOAL":         "is a goal of",
    "SEQUENCE":     "is followed by",
    "SIMILARITY":   "is similar to",
}

# ── Reasoning mode keywords ────────────────────────────────────────────────────
CAUSAL_KEYWORDS    = {"why", "cause", "because", "reason", "leads", "results"}
TEMPORAL_KEYWORDS  = {"when", "before", "after", "during", "then", "sequence", "order", "first", "next"}
ANALOGY_KEYWORDS   = {"like", "similar", "analogy", "compare", "same", "equivalent"}
PLANNING_KEYWORDS  = {"plan", "goal", "achieve", "how to", "steps", "strategy"}
PREDICTION_KEYWORDS = {"predict", "will", "future", "expect", "outcome", "likely"}
CONTRADICTION_KEYWORDS = {"but", "however", "contradict", "conflict", "opposite", "disagree"}
