"""
synthetic/training/generator.py — Synthetic graph topology generator.
"""
from __future__ import annotations

import hashlib
from typing import List, Dict, Tuple
from core.enums import EdgeType
from graph.graph import CognitiveGraph
from graph.node import Node
from graph.edge import Edge


class SyntheticGraphGenerator:
    """
    Generates synthetic graph structures for training and evaluation.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def generate_chain(self, labels: List[str], edge_type: EdgeType = EdgeType.CAUSES) -> List[str]:
        """Creates a linear chain of concepts."""
        node_ids = []
        for label in labels:
            nid = self._get_id(label)
            if not self.graph.get_node(nid):
                self.graph.add_node(Node(id=nid, label=label))
            node_ids.append(nid)
            
        for i in range(len(node_ids) - 1):
            self.graph.add_edge(Edge(
                source=node_ids[i],
                target=node_ids[i+1],
                edge_type=edge_type,
                weight=0.9
            ))
        return node_ids

    def generate_isomorphism(self, source_labels: List[str], target_labels: List[str], edge_types: List[EdgeType]):
        """Creates two identical structures with different labels (for analogy testing)."""
        if len(source_labels) != len(target_labels) or len(source_labels) < 2:
            return
            
        self.generate_chain(source_labels, edge_types[0])
        self.generate_chain(target_labels, edge_types[0])

    def _get_id(self, label: str) -> str:
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
