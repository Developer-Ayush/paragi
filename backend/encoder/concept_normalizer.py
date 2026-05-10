"""
encoder/concept_normalizer.py — Normalize concepts to canonical forms.
"""
from __future__ import annotations

import re


class ConceptNormalizer:
    """
    Normalizes concept labels to ensure graph consistency.
    Example: "burning" -> "burn", "Fire!" -> "fire".
    """

    def normalize(self, label: str) -> str:
        # Lowercase and strip
        normalized = label.lower().strip()
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Basic lemmatization heuristics (simple for now)
        if normalized.endswith("ing") and len(normalized) > 5:
            normalized = normalized[:-3]
        elif normalized.endswith("s") and len(normalized) > 3 and not normalized.endswith("ss"):
            normalized = normalized[:-1]
            
        return normalized
