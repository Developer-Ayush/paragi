"""
reasoning/temporal_reasoner.py — Temporal reasoning and sequencing.
"""
from __future__ import annotations

import hashlib
from typing import Dict, Any, List
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from graph.graph import CognitiveGraph
from graph.traversal.constrained import constrained_traversal


class TemporalReasoner:
    """
    Reasoning by following TEMPORAL and SEQUENCE edges.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def reason(self, ir: SemanticIR) -> Dict[str, Any]:
        # 1. Identify anchor event
        anchor = ir.entities[0] if ir.entities else None
        if not anchor:
            return {"error": "No temporal anchor identified"}
            
        anchor_id = self._get_node_id(anchor)
        
        # 2. Trace timeline
        timeline = constrained_traversal(
            self.graph, anchor_id,
            allowed_edge_types=[EdgeType.TEMPORAL, EdgeType.SEQUENCE],
            max_depth=5
        )
        
        # 3. Format results
        events = []
        for src_id, _, tgt_id in timeline:
            if not events:
                src_node = self.graph.get_node(src_id)
                if src_node: events.append(src_node.label)

            tgt_node = self.graph.get_node(tgt_id)
            if tgt_node and tgt_node.label not in events:
                events.append(tgt_node.label)
        
        return {
            "mode": "temporal",
            "anchor": anchor,
            "timeline": events
        }

    def _get_node_id(self, label: str) -> str:
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
