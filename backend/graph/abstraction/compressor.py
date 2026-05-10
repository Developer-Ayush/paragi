"""graph/abstraction/compressor.py — Semantic compression logic."""
from __future__ import annotations
from typing import List
from graph.graph_store import GraphStore
from graph.node import Node

class SemanticCompressor:
    """
    Compresses dense graph regions into higher-level abstract nodes.
    Reduces cognitive load by replacing N concrete nodes with 1 abstract node.
    """
    def __init__(self, store: GraphStore):
        self.store = store

    def compress(self, node_ids: List[str], abstract_label: str) -> str:
        """Create an abstract node representing a cluster of concrete nodes."""
        if not node_ids:
            return ""
            
        from core.types import make_node_id
        abstract_id = make_node_id(abstract_label)
        
        # Check if already exists
        existing = self.store.get_node(abstract_id)
        if not existing:
            abstract_node = Node.create(abstract_id, abstract_label, abstraction_level=1)
            self.store.add_node(abstract_node)
        
        # In a real system, we'd link the concrete nodes to the abstract node
        # via ABSTRACTS_TO edges here.
        return abstract_id
