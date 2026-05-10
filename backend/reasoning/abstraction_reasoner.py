"""
reasoning/abstraction_reasoner.py — Abstraction and hierarchy reasoning.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Any, List
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from graph.graph import CognitiveGraph


class AbstractionReasoner:
    """
    Reasoning by moving up (generalizing) or down (specializing) the graph hierarchy.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def reason(self, ir: SemanticIR) -> Dict[str, Any]:
        # 1. Identify starting point
        start = ir.entities[0] if ir.entities else None
        if not start:
            return {"error": "No concept for abstraction"}
            
        start_id = self._get_node_id(start)
        
        # 2. Find generalizations (ABSTRACTS_TO, IS_A)
        generalizations = []
        for edge in self.graph.get_outgoing_edges(start_id):
            if edge.edge_type in [EdgeType.ABSTRACTS_TO, EdgeType.IS_A]:
                generalizations.append(self.graph.get_node(edge.target).label)
                
        # 3. Find specializations (inverse of ABSTRACTS_TO, IS_A)
        specializations = []
        for edge in self.graph.get_incoming_edges(start_id):
            if edge.edge_type in [EdgeType.ABSTRACTS_TO, EdgeType.IS_A]:
                specializations.append(self.graph.get_node(edge.source).label)
                
        return {
            "mode": "abstraction",
            "concept": start,
            "is_a": generalizations,
            "includes": specializations
        }

    def _get_node_id(self, label: str) -> str:
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
