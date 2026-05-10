"""reasoning/meta_reasoner.py — Meta-level reasoning strategy selection."""
from __future__ import annotations

class MetaReasoner:
    """Evaluates the graph state to decide which subset of reasoners to deploy."""
    def select_strategy(self, available_edges: list) -> str:
        return "general"
