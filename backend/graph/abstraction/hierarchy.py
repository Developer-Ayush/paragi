"""graph/abstraction/hierarchy.py — Abstract hierarchy management."""
from __future__ import annotations
from graph.graph_store import GraphStore

class HierarchyManager:
    """Manages IS_A and ABSTRACTS_TO hierarchical taxonomies in the graph."""
    def __init__(self, store: GraphStore):
        self.store = store

    def get_ancestors(self, node_id: str, max_depth: int = 5) -> list[str]:
        """Traverse upward to find abstract categories."""
        return []

    def get_descendants(self, node_id: str, max_depth: int = 5) -> list[str]:
        """Traverse downward to find concrete instances."""
        return []
