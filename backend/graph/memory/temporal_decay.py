"""graph/memory/temporal_decay.py — Memory decay orchestrator."""
from __future__ import annotations
from graph.graph_store import GraphStore

class TemporalDecayManager:
    """Manages the forgetting curve of nodes and edges over time."""
    def __init__(self, store: GraphStore):
        self.store = store

    def apply_decay(self, current_time: float) -> None:
        """Apply temporal decay to all unstabilized graph elements."""
        pass
