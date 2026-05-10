"""graph/activation/__init__.py"""
from .spread import spread_activation
from .salience import get_salient_nodes as detect_salience
from .decay import apply_global_decay as apply_temporal_decay
from .attention import AttentionController

__all__ = [
    "spread_activation",
    "detect_salience",
    "apply_temporal_decay",
    "AttentionController"
]
