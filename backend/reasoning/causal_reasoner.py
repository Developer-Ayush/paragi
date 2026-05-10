"""
reasoning/causal_reasoner.py — Causal inference engine.
"""
from __future__ import annotations

from typing import Dict, Any, List
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from graph.graph import CognitiveGraph
from graph.activation.spread import spread_activation
from graph.traversal.constrained import constrained_traversal


class CausalReasoner:
    """
    Reasoning by following CAUSES edges and spreading activation.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def reason(self, ir: SemanticIR) -> Dict[str, Any]:
        """
        Perform causal inference based on SemanticIR.
        """
        # 1. Identify source concepts
        sources = ir.entities + ir.concepts
        if not sources:
            return {"error": "No causal sources identified"}
            
        source_ids = [self._get_node_id(s) for s in sources]
        source_ids = [sid for sid in source_ids if sid] # Filter None
        
        # 2. Pulse activation into sources
        activated_nodes = {}
        for sid in source_ids:
            deltas = spread_activation(self.graph, sid, initial_energy=1.0)
            activated_nodes.update(deltas)
            
        # 3. Find causal chains (constrained traversal)
        causal_chains = []
        for sid in source_ids:
            chain = constrained_traversal(
                self.graph, sid, 
                allowed_edge_types=[EdgeType.CAUSES, EdgeType.ASSOCIATED_WITH, EdgeType.IS_A],
                max_depth=4
            )
            if len(chain) > 1:
                causal_chains.append(chain)
                
        # 4. Map back to human-readable labels
        results = []
        for chain in causal_chains:
            labels = []
            for nid in chain:
                node = self.graph.get_node(nid)
                if node:
                    labels.append(node.label)
            if labels:
                results.append(" -> ".join(labels))
            
        # Filter activated nodes to only those that exist
        active_labels = []
        for nid in activated_nodes:
            node = self.graph.get_node(nid)
            if node:
                active_labels.append(node.label)
                
        return {
            "mode": "causal",
            "chains": results,
            "activated_concepts": active_labels
        }

    def _get_node_id(self, label: str) -> Optional[str]:
        # Helper to find node ID by label (should probably be in CognitiveGraph)
        import hashlib
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
