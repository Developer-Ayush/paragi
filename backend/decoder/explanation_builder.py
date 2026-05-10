"""
decoder/explanation_builder.py — Path-to-narrative conversion.
"""
from __future__ import annotations

from typing import List, Dict, Any


class ExplanationBuilder:
    """
    Builds narrative explanations from reasoning paths.
    """

    def build_narrative(self, meaning: Dict[str, Any]) -> str:
        """
        Converts meaning representation into a draft narrative.
        """
        facts = meaning.get("facts", [])
        if not facts:
            # Fallback to chains
            chains = meaning.get("chains", [])
            if not chains:
                return "I couldn't find a clear explanation in the knowledge graph."
            return ". ".join(chains) + "."

        # Capitalize and join facts
        sentences = [f"{f[0].upper() + f[1:]}." for f in facts if f]
        return " ".join(sentences)
