from typing import Set
from core.semantic_ir import SemanticIR

class AttentionSystem:
    """
    Modulates spreading activation based on the current focus.
    """
    def __init__(self):
        self.focus_nodes: Set[str] = set()

    def update_focus(self, ir: SemanticIR):
        """Extract focus nodes from the current SemanticIR."""
        self.focus_nodes = set(ir.activation_targets)

    def get_attention_weight(self, node_id: str) -> float:
        """Return a weight multiplier for activation reaching this node."""
        if node_id in self.focus_nodes:
            return 1.5
        return 1.0
