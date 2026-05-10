"""graph/contradiction/confidence.py — Confidence weighting for resolving disputes."""
from __future__ import annotations

def calculate_resolution_confidence(positive_weight: float, negative_weight: float) -> float:
    """Calculate confidence when resolving contradictory edges."""
    total = positive_weight + negative_weight
    if total == 0: return 0.0
    return abs(positive_weight - negative_weight) / total
