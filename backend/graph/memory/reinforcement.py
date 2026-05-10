"""graph/memory/reinforcement.py — Hebbian reinforcement coordinator."""
from __future__ import annotations
from graph.graph_store import GraphStore
from core.logger import get_logger

log = get_logger(__name__)

class ReinforcementManager:
    """Coordinates the strengthening of successfully traversed reasoning paths."""
    def __init__(self, store: GraphStore):
        self.store = store

    def reinforce_path(self, path_edge_ids: list[str]) -> None:
        """Apply Hebbian updates to a sequence of edges."""
        count = 0
        for edge_id in path_edge_ids:
            edge = self.store.get_edge(edge_id)
            if edge:
                edge.reinforce()
                count += 1
        
        if count > 0:
            log.debug(f"Reinforced {count} edges along cognitive path.")
