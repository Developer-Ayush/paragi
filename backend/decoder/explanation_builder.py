"""
decoder/explanation_builder.py — Builds narrative explanations from graph paths.
"""
from __future__ import annotations

from typing import Dict, Any, List


class ExplanationBuilder:
    """
    Constructs human-readable explanations of graph traversal.
    """

    def build_narrative(self, meaning: Dict[str, Any]) -> str:
        """
        Builds a base narrative from graph facts.
        """
        facts = meaning.get("facts", [])
        if not facts:
            return ""

        # Basic joining logic
        # OpenRouter will later refine this into high-quality text.
        return ". ".join(facts) + "."

    def describe_path(self, path_labels: List[str]) -> str:
        """
        Describes a traversal path in plain text.
        """
        if not path_labels:
            return ""
        return " -> ".join(path_labels)
