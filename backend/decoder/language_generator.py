"""decoder/language_generator.py — Language generation at the decoder boundary.

Ports LLMRefiner.format_response() into the new decoder architecture.
LLM is only called here — the decoder boundary.
"""
from __future__ import annotations
from typing import Any, List, Optional
from .own_decoder import OwnDecoder
from .semantic_reconstruction import reconstruct_from_path


class LanguageGenerator:
    """
    Decoder boundary: converts graph reasoning result → human language.

    When LLM is available: calls format_response.
    When LLM is disabled: delegates to OwnDecoder templates.
    """

    def __init__(self, *, llm_refiner: Any = None, own_decoder: Optional[OwnDecoder] = None) -> None:
        self._llm = llm_refiner
        self._own = own_decoder or OwnDecoder()

    def generate(
        self,
        *,
        question: str,
        graph_answer: str,
        node_path: List[str],
        edge_types: List[str],
        confidence: float,
        intent_kind: str = "unknown",
    ) -> str:
        """Generate a human-readable answer."""

        # If answer is empty, no LLM call needed
        if not graph_answer and confidence < 0.1:
            return ""

        # Use LLM at decoder boundary if available
        if self._llm is not None:
            try:
                result = self._llm.format_response(
                    question=question,
                    graph_answer=graph_answer,
                    node_path=node_path,
                    confidence=confidence,
                    intent_kind=intent_kind,
                )
                if result.used and result.answer:
                    return result.answer
            except Exception:
                pass

        # Fallback: OwnDecoder template
        if graph_answer:
            return self._own.decode(graph_answer, confidence, node_path)

        # Last fallback: reconstruct from path
        if node_path and edge_types:
            reconstructed = reconstruct_from_path(node_path, edge_types)
            return self._own.decode(reconstructed, confidence, node_path)

        return ""
