"""reasoning/activation_controller.py — Controls spreading activation thresholds."""
from __future__ import annotations

class ActivationController:
    """Dynamically adjusts graph spreading activation parameters based on query context."""
    def calculate_decay_rate(self, intent: str, domain: str = "general") -> float:
        """Deep explorative queries get lower decay (spread further)."""
        if intent in ("exploratory", "analogy_question"):
            return 0.2  # Reach further
        if intent in ("fact_retrieval", "personal_query"):
            return 0.8  # Stop quickly
        return 0.5
