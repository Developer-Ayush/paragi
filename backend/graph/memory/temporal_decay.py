"""graph/memory/temporal_decay.py — Memory decay orchestrator."""
from __future__ import annotations
from graph.graph_store import GraphStore
import time

class TemporalDecayManager:
    """Manages the forgetting curve of nodes and edges over time."""
    def __init__(self, store: GraphStore):
        self.store = store

    def apply_decay(self, base_rate: float = 0.05) -> int:
        """Apply temporal decay to all unstabilized graph elements."""
        now = time.time()
        decayed_count = 0
        
        # Needs to lock while iterating in a real multi-threaded environment
        with self.store._lock:
            for edge in self.store._edges.values():
                # Don't decay highly stable structural edges immediately
                if edge._data.stability < 1.0 or edge.strength < 0.9:
                    edge.decay(base_rate)
                    decayed_count += 1
                    
            for node in self.store._nodes.values():
                # Just trigger the salience re-calculation based on time
                _ = node.compute_salience(now)
                
        return decayed_count
