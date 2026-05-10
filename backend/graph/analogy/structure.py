"""graph/analogy/structure.py — Subgraph structural definitions for analogies."""
from __future__ import annotations

class AnalogyStructure:
    """Represents a relational subgraph structure used for analogical mapping."""
    def __init__(self, root: str, relations: list[dict]):
        self.root = root
        self.relations = relations  # e.g., [{"type": "CAUSES", "target_degree": 2}]
        
    def signature(self) -> str:
        """Computes a structural hash for quick analogy candidate retrieval."""
        sigs = [f"{r.get('type')}:{r.get('target_degree', 0)}" for r in self.relations]
        return "-".join(sorted(sigs))
