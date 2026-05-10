"""
decoder/semantic_reconstruction.py — Reconstruct meaning from SemanticIR.
"""
from __future__ import annotations

from typing import List, Dict, Any
from core.semantic_ir import SemanticIR


class SemanticReconstructor:
    """
    Converts a populated SemanticIR into a structured "Meaning Representation".
    """

    def reconstruct(self, ir: SemanticIR) -> Dict[str, Any]:
        """
        Builds a structured summary of the information to be communicated.
        """
        # 1. Primary subject
        subject = ir.entities[0] if ir.entities else "The system"
        
        # 2. Key facts (relations)
        facts = []
        for rel in ir.relations:
            facts.append(f"{rel.source} {self._get_rel_verb(rel.relation)} {rel.target}")
            
        # 3. Chains (from reasoning)
        chains = ir.metadata.get("chains", [])
        
        return {
            "subject": subject,
            "facts": facts,
            "chains": chains,
            "mode": ir.metadata.get("reasoning_mode", "general")
        }

    def _get_rel_verb(self, rel_type: str) -> str:
        # Simple mapping for internal relations to natural language verbs
        mapping = {
            "CAUSES": "causes",
            "IS_A": "is a",
            "PART_OF": "is part of",
            "ASSOCIATED_WITH": "is associated with",
            "ANALOGY": "is similar to",
            "TEMPORAL": "is followed by"
        }
        return mapping.get(str(rel_type), "relates to")
