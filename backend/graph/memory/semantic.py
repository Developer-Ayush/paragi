"""
graph/memory/semantic.py — Semantic Memory.

The long-term permanent knowledge graph of the system.
"""
from __future__ import annotations

from typing import List, Optional
from ..graph import CognitiveGraph
from ..node import Node


class SemanticMemory:
    """
    Interface for interacting with the permanent cognitive graph.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def query_concept(self, label: str) -> Optional[Node]:
        """Find a concept in semantic memory by label."""
        # Simple lookup in graph cache
        for node in self.graph._nodes.values():
            if node.label.lower() == label.lower():
                return node
        return None

    def get_related_concepts(self, node_id: str) -> List[Node]:
        """Retrieve 1-hop neighbors from semantic memory."""
        neighbors = []
        for edge in self.graph.get_outgoing_edges(node_id):
            target = self.graph.get_node(edge.target)
            if target:
                neighbors.append(target)
        return neighbors
