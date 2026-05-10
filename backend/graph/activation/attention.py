"""
graph/activation/attention.py — Graph-native attention mechanism.

Focuses reasoning resources on high-salience subgraphs.
"""
from __future__ import annotations

from typing import Set, List
from ..graph import CognitiveGraph
from .salience import get_salient_nodes


class AttentionController:
    """
    Manages the 'focus' of the cognitive system.
    Identifies which nodes should be actively processed.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph
        self.focal_nodes: Set[str] = set()

    def update_focus(self, limit: int = 5) -> Set[str]:
        """
        Updates the set of focal nodes based on current salience.
        """
        salient = get_salient_nodes(self.graph, limit=limit)
        self.focal_nodes = {nid for nid, score in salient}
        return self.focal_nodes

    def is_focal(self, node_id: str) -> bool:
        """Check if a node is currently in focus."""
        return node_id in self.focal_nodes

    def get_attended_subgraph(self) -> CognitiveGraph:
        """
        Extracts the subgraph containing all focal nodes and their 1-hop neighbors.
        """
        nodes_to_extract = set(self.focal_nodes)
        for focal_id in self.focal_nodes:
            for edge in self.graph.get_outgoing_edges(focal_id):
                nodes_to_extract.add(edge.target)
            for edge in self.graph.get_incoming_edges(focal_id):
                nodes_to_extract.add(edge.source)
                
        return self.graph.extract_subgraph(nodes_to_extract)
