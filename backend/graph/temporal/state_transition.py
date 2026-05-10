"""graph/temporal/state_transition.py — Temporal state transitions."""
from __future__ import annotations

class StateTransition:
    """Represents a change in semantic state over time."""
    def __init__(self, node_id: str, pre_state: str, post_state: str, trigger: str = None):
        self.node_id = node_id
        self.pre_state = pre_state
        self.post_state = post_state
        self.trigger = trigger
        
    def is_reversible(self) -> bool:
        """Check if transition is known to be reversible."""
        return self.pre_state in ("active", "inactive") and self.post_state in ("active", "inactive")
