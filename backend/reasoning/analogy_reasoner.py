"""
reasoning/analogy_reasoner.py — Analogical reasoning via structural graph mapping.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Any, List, Set, Optional
from core.semantic_ir import SemanticIR
from graph.graph import CognitiveGraph


class AnalogyReasoner:
    """
    Reasoning by finding isomorphic or structurally similar subgraphs.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def reason(self, ir: SemanticIR) -> Dict[str, Any]:
        # 1. Identify source domain
        source = ir.entities[0] if ir.entities else None
        if not source:
            return {"error": "No analogy source identified"}
            
        source_id = self._get_node_id(source)
        if not source_id:
            return {"error": f"Concept '{source}' not found in memory"}
            
        # 2. Extract source structure (neighborhood)
        source_neighbors = self.graph.get_outgoing_edges(source_id)
        source_pattern = {(e.edge_type, e.target) for e in source_neighbors}
        
        # 3. Find structural candidates
        candidates = []
        for nid, node in self.graph._nodes.items():
            if nid == source_id: continue
            
            # Simple structural similarity: shared edge types and topology
            candidate_neighbors = self.graph.get_outgoing_edges(nid)
            candidate_pattern = {(e.edge_type, e.target) for e in candidate_neighbors}
            
            # Intersection of edge types
            source_types = {p[0] for p in source_pattern}
            candidate_types = {p[0] for p in candidate_pattern}
            shared_types = source_types & candidate_types
            
            if shared_types:
                score = len(shared_types) / len(source_types) if source_types else 0
                if score > 0.5:
                    candidates.append({
                        "concept": node.label,
                        "score": score,
                        "shared_logic": list(shared_types)
                    })
                    
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "mode": "analogy",
            "source": source,
            "candidates": candidates[:5]
        }

    def _get_node_id(self, label: str) -> str:
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
