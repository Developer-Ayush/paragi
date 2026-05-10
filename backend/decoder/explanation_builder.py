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
        chains = meaning.get("chains", [])
        if not chains:
            # Fallback to facts
            facts = meaning.get("facts", [])
            if not facts:
                return "I couldn't find a clear explanation."
            return ". ".join(facts) + "."

        # Convert chains to steps
        narratives = []
        for chain in chains:
            steps = chain.split(" -> ")
            if len(steps) > 1:
                narrative = f"Starting with {steps[0]}, we see that it leads to {steps[1]}"
                for i in range(2, len(steps)):
                    narrative += f", which then results in {steps[i]}"
                narratives.append(narrative)
                
        return ". ".join(narratives) + "."
