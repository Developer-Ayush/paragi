"""graph/analogy/structure.py — Subgraph structural definitions for analogies."""
from __future__ import annotations

class AnalogyStructure:
    """Represents a relational subgraph structure used for analogical mapping."""
    def __init__(self, root: str, relations: list[dict]):
        self.root = root
        self.relations = relations
