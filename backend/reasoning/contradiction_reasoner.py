"""
reasoning/contradiction_reasoner.py — Logical contradiction detection and resolution.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Any, List
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from graph.graph import CognitiveGraph


class ContradictionReasoner:
    """
    Detects and resolves conflicting paths or edges in the graph.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def reason(self, ir: SemanticIR) -> Dict[str, Any]:
        # 1. Identify primary concept
        subject = ir.entities[0] if ir.entities else None
        if not subject:
            return {"error": "No subject for contradiction check"}
            
        subject_id = self._get_node_id(subject)
        
        # 2. Check for explicit CONTRADICTS edges
        conflicts = []
        for edge in self.graph.get_outgoing_edges(subject_id):
            if edge.edge_type == EdgeType.CONTRADICTS:
                conflicts.append({
                    "subject": subject,
                    "contradicts": self.graph.get_node(edge.target).label,
                    "confidence": edge.confidence
                })
                
        # 3. Check for implicit contradictions (same path, different target)
        # (Implementation placeholder for deeper path contradiction logic)
        
        return {
            "mode": "contradiction",
            "subject": subject,
            "conflicts": conflicts
        }

    def _get_node_id(self, label: str) -> str:
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
