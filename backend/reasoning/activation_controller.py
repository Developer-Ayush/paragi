"""reasoning/activation_controller.py — Controls spreading activation thresholds."""
from __future__ import annotations

class ActivationController:
    """Dynamically adjusts graph spreading activation parameters based on query context."""
    def calculate_decay_rate(self, intent: str) -> float:
        return 0.5
