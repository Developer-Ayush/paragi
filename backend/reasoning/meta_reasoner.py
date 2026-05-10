"""reasoning/meta_reasoner.py — Meta-level reasoning strategy selection."""
from __future__ import annotations

class MetaReasoner:
    """Evaluates the graph state to decide which subset of reasoners to deploy."""
    def select_strategy(self, available_edges: list[object]) -> str:
        """Examine edges connected to query focal nodes to select reasoning type."""
        type_counts = {}
        for edge in available_edges:
            t = edge.type.value if hasattr(edge, "type") else edge.get("type")
            type_counts[t] = type_counts.get(t, 0) + 1
            
        if type_counts.get("CAUSES", 0) > 0:
            return "causal"
        if type_counts.get("TEMPORAL", 0) > 0 or type_counts.get("SEQUENCE", 0) > 0:
            return "temporal"
        if type_counts.get("IS_A", 0) > 0 or type_counts.get("ABSTRACTS_TO", 0) > 0:
            return "abstraction"
            
        return "general"
