"""graph/abstraction/hierarchy.py — Abstract hierarchy management."""
from __future__ import annotations
from graph.graph_store import GraphStore
from core.enums import EdgeType

class HierarchyManager:
    """Manages IS_A and ABSTRACTS_TO hierarchical taxonomies in the graph."""
    def __init__(self, store: GraphStore):
        self.store = store

    def get_ancestors(self, node_id: str, max_depth: int = 5) -> list[str]:
        """Traverse upward to find abstract categories."""
        ancestors = []
        current_layer = [node_id]
        visited = {node_id}
        
        for _ in range(max_depth):
            next_layer = []
            for current_id in current_layer:
                outgoing = self.store.get_outgoing(current_id)
                for edge in outgoing:
                    if edge.type in (EdgeType.IS_A, EdgeType.ABSTRACTS_TO):
                        if edge.target not in visited:
                            visited.add(edge.target)
                            next_layer.append(edge.target)
                            ancestors.append(edge.target)
            current_layer = next_layer
            if not current_layer:
                break
        return ancestors

    def get_descendants(self, node_id: str, max_depth: int = 5) -> list[str]:
        """Traverse downward to find concrete instances."""
        descendants = []
        current_layer = [node_id]
        visited = {node_id}
        
        for _ in range(max_depth):
            next_layer = []
            for current_id in current_layer:
                incoming = self.store.get_incoming(current_id)
                for edge in incoming:
                    if edge.type in (EdgeType.IS_A, EdgeType.ABSTRACTS_TO):
                        if edge.source not in visited:
                            visited.add(edge.source)
                            next_layer.append(edge.source)
                            descendants.append(edge.source)
            current_layer = next_layer
            if not current_layer:
                break
        return descendants
