"""
decoder/language_generator.py — Fluency layer and text generation.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from utils.llm_refiner import LLMRefiner
from .explanation_builder import ExplanationBuilder


class LanguageGenerator:
    """
    Translates the meaning representation into fluent natural language.
    """

    def __init__(self, llm_refiner: Optional[LLMRefiner] = None) -> None:
        self.refiner = llm_refiner
        self.explanation_builder = ExplanationBuilder()

    def generate(self, meaning: Dict[str, Any], original_query: str = "") -> str:
        """
        Produces the final natural language response.
        """
        # 1. Build base narrative from graph structure
        base_narrative = self.explanation_builder.build_narrative(meaning)
        
        # 2. Refine with LLM for fluency (if available)
        if self.refiner:
            # We adapt meaning to RefineResult format
            refine_res = self.refiner.format_response(
                question=original_query,
                graph_answer=base_narrative,
                node_path=meaning.get("chains", []),
                confidence=0.8, # Default for reasoning results
                intent_kind=meaning.get("mode", "general")
            )
            return refine_res.answer
            
        return base_narrative
