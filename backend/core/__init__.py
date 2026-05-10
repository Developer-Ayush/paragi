"""core/__init__.py — Core package exports."""
from .config import Settings
from .constants import (
    VECTOR_SIZE, SEMANTIC_DIMS,
    EDGE_STRENGTH_FLOOR, EDGE_DECAY_PER_CYCLE, EDGE_PRUNE_THRESHOLD,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW, LEARNING_THRESHOLD,
    DEFAULT_MAX_HOPS, DEFAULT_MAX_PATHS,
    EDGE_RELATION_TEXT,
)
from .enums import (
    EdgeType, QueryType, ReasoningMode, MemoryType, NodeType, ActivationState,
)
from .exceptions import (
    ParagiError, EncoderError, GraphError, ReasoningError,
    DecoderError, CognitionError, StorageError, ConfigError,
)
from .logger import get_logger
from .semantic_ir import Relation, SemanticIR, TemporalData
from .types import (
    NodeID, EdgeID, Vector, SemanticVector,
    NodeRecord, EdgeRecord,
    normalize_label, normalize_label_raw,
    make_node_id, make_edge_id, now_ts,
)

__all__ = [
    # Config
    "Settings",
    # Constants
    "VECTOR_SIZE", "SEMANTIC_DIMS",
    "EDGE_STRENGTH_FLOOR", "EDGE_DECAY_PER_CYCLE", "EDGE_PRUNE_THRESHOLD",
    "CONFIDENCE_HIGH", "CONFIDENCE_MEDIUM", "CONFIDENCE_LOW", "LEARNING_THRESHOLD",
    "DEFAULT_MAX_HOPS", "DEFAULT_MAX_PATHS", "EDGE_RELATION_TEXT",
    # Enums
    "EdgeType", "QueryType", "ReasoningMode", "MemoryType", "NodeType", "ActivationState",
    # Exceptions
    "ParagiError", "EncoderError", "GraphError", "ReasoningError",
    "DecoderError", "CognitionError", "StorageError", "ConfigError",
    # Logger
    "get_logger",
    # SemanticIR
    "Relation", "SemanticIR", "TemporalData",
    # Types
    "NodeID", "EdgeID", "Vector", "SemanticVector",
    "NodeRecord", "EdgeRecord",
    "normalize_label", "normalize_label_raw",
    "make_node_id", "make_edge_id", "now_ts",
]
