"""graph/contradiction/confidence.py — Confidence weighting for resolving disputes."""
from __future__ import annotations

def calculate_resolution_confidence(positive_weight: float, negative_weight: float) -> float:
    """Calculate confidence when resolving contradictory edges."""
    total = positive_weight + negative_weight
    if total == 0: return 0.0
    
    # Margin of victory
    margin = abs(positive_weight - negative_weight)
    
    # High confidence if margin is large relative to total
    confidence = margin / total
    
    # Scale down if total evidence is very low
    if total < 1.0:
        confidence *= total
        
    return min(1.0, confidence)
