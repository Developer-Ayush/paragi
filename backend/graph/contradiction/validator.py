"""graph/contradiction/validator.py — Logical contradiction validation."""
from __future__ import annotations
from graph.graph_store import GraphStore
from core.enums import EdgeType

class ContradictionValidator:
    """Validates if two incoming facts logically contradict existing knowledge."""
    def __init__(self, store: GraphStore):
        self.store = store

    def check_validity(self, source: str, relation: str, target: str) -> bool:
        """Returns False if the new relation directly contradicts strong existing facts."""
        if relation == "CAUSES":
            # If A CAUSES B is proposed, but A CONTRADICTS B exists
            outgoing = self.store.get_outgoing(source)
            for edge in outgoing:
                if edge.target == target and edge.type == EdgeType.CONTRADICTS and edge.strength > 0.6:
                    return False
        return True
