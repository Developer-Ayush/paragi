"""
encoder/semantic_encoder.py — Orchestrate text-to-SemanticIR conversion via OpenRouter.
"""
from __future__ import annotations

from typing import List, Dict, Any, TYPE_CHECKING
from core.semantic_ir import SemanticIR, IRRelation
from core.logger import get_logger
from core.enums import EdgeType

if TYPE_CHECKING:
    from utils.llm_refiner import LLMRefiner

log = get_logger(__name__)


class SemanticEncoder:
    """
    Coordinates extraction and classification to produce a SemanticIR using OpenRouter.
    """

    def __init__(self, llm: LLMRefiner | None = None):
        self.llm = llm

    def encode(self, text: str) -> SemanticIR:
        """Process raw text into SemanticIR using LLM-first strategy."""
        log.info(f"Encoding text via LLM: {text}")
        
        if not self.llm or self.llm.backend == "none":
            # Fallback to legacy heuristic if no LLM
            from .parser import parse
            from .entity_extractor import extract_entities
            from .relation_extractor import extract_relations
            from .intent_classifier import classify
            
            parsed = parse(text)
            extracted = extract_entities(parsed)
            relations = extract_relations(parsed)
            intent_info = classify(parsed)

            return SemanticIR(
                text=text,
                entities=extracted.entities,
                concepts=extracted.noun_phrases,
                relations=relations,
                intent=intent_info.kind,
                confidence=intent_info.confidence,
                metadata={"reasoning_mode": intent_info.mode.value}
            )

        # ── Step 1: OpenRouter Parse ──────────────────────────────────────────
        parsed = self.llm.parse_intent(text)

        # ── Step 2: Convert to IRRelations ─────────────────────────────────────
        ir_relations = []
        for edge in parsed.graph_edges:
            try:
                rel = IRRelation(
                    source=edge["source"],
                    relation=EdgeType.get(edge["relation"], EdgeType.ASSOCIATED_WITH),
                    target=edge["target"],
                    confidence=edge.get("confidence", 0.9)
                )
                ir_relations.append(rel)
            except Exception as e:
                log.warning(f"Failed to parse LLM edge: {edge} -> {e}")

        # ── Step 3: Build SemanticIR ──────────────────────────────────────────
        ir = SemanticIR(
            text=text,
            entities=parsed.entities,
            concepts=parsed.concepts,
            relations=ir_relations,
            intent=parsed.kind,
            confidence=parsed.learnability,
            metadata={
                "query_type": parsed.query_type,
                "emotional_tone": parsed.emotional_tone,
                "requires_web": parsed.requires_web,
                "reasoning_mode": "general"
            }
        )
        
        return ir
