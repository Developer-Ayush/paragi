"""
decoder/language_generator.py — Generate natural language via OpenRouter.
"""
from __future__ import annotations

from typing import Dict, Any, TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    from utils.llm_refiner import LLMRefiner

log = get_logger(__name__)


class LanguageGenerator:
    """
    Produces final natural language responses using OpenRouter refinement.
    """

    def __init__(self, llm_refiner: LLMRefiner) -> None:
        self.llm = llm_refiner

    def generate(self, reasoning_result: Dict[str, Any], original_query: str) -> str:
        """
        Takes graph reasoning facts and produces a fluent response.
        """
        facts = reasoning_result.get("facts", [])
        chains = reasoning_result.get("chains", [])

        # Merge all found knowledge into a context string
        base_context = ". ".join(list(set(facts + chains)))

        if not self.llm or self.llm.backend == "none":
            return base_context if base_context else "I don't have enough information to answer that."

        # Use OpenRouter to refine the facts into a "sleek" response
        refinement = self.llm.format_response(
            question=original_query,
            graph_answer=base_context,
            node_path=reasoning_result.get("activated_concepts", []),
            confidence=0.9 if base_context else 0.0,
            intent_kind=reasoning_result.get("mode", "general")
        )
        
        return refinement.answer
