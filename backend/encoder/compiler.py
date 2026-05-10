"""encoder/compiler.py — SemanticCompiler: the full semantic compilation pipeline.

This is the encoder boundary between human language and the cognitive graph.

    Human Language → SemanticCompiler → SemanticIR

The compiler DOES NOT reason. It only extracts meaning.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.semantic_ir import Relation, SemanticIR, TemporalData
from core.logger import get_logger

from .parser import parse
from .intent_classifier import classify, IntentClassification
from .entity_extractor import extract_entities
from .relation_extractor import extract_relations
from .concept_normalizer import normalize_concept, normalize_concepts
from .embedding_encoder import EmbeddingEncoder
from .semantic_mapper import map_to_graph_concepts
from .ambiguity_resolver import resolve_batch
from .context_builder import build_context

log = get_logger(__name__)

_TEMPORAL_KEYWORDS = {"before", "after", "when", "then", "first", "next", "finally", "during"}
_REALTIME_KEYWORDS = {"news", "today", "current", "latest", "now", "weather", "stock", "live"}


class SemanticCompiler:
    """
    The encoder / semantic compiler.

    Transforms raw human language into a SemanticIR object.
    All downstream components (graph, reasoning, decoder) consume SemanticIR.

    The compiler must NOT perform reasoning. It only extracts structure.
    """

    def __init__(self, *, use_fastembed: bool = False, llm_refiner: Any = None) -> None:
        self._embedding_encoder = EmbeddingEncoder(use_fastembed=use_fastembed)
        self._llm = llm_refiner  # Optional LLM for intent enhancement

    def compile(
        self,
        text: str,
        *,
        user_id: str = "guest",
        chat_id: Optional[str] = None,
        scope: str = "main",
        domain: str = "general",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        user_state: Optional[Dict[str, Any]] = None,
        is_realtime: bool = False,
    ) -> SemanticIR:
        """
        Compile raw text into a SemanticIR.

        Steps:
          1. Parse (normalize, tokenize, sentence-split)
          2. Classify intent (regex + optional LLM)
          3. Extract entities and resolve ambiguity
          4. Extract relations
          5. Normalize concepts
          6. Encode semantic embedding
          7. Build context
          8. Assemble SemanticIR
        """
        # ── 1. Parse ──────────────────────────────────────────────────────
        parsed = parse(text)

        # ── 2. Intent classification ──────────────────────────────────────
        intent_cls: IntentClassification = classify(parsed)
        llm_edges: List[Dict[str, Any]] = []

        # Optional LLM enhancement (at encoder boundary only)
        if self._llm is not None:
            try:
                llm_result = self._llm.parse_intent(text)
                if llm_result and llm_result.kind != "unknown" and not llm_result.error:
                    intent_cls.kind = llm_result.kind
                    intent_cls.source = llm_result.source or intent_cls.source
                    intent_cls.target = llm_result.target or intent_cls.target
                    intent_cls.concept = llm_result.concept or intent_cls.concept
                    intent_cls.personal_attribute = llm_result.personal_attribute or intent_cls.personal_attribute
                    intent_cls.personal_value = llm_result.personal_value or intent_cls.personal_value
                    intent_cls.query_type = llm_result.query_type or intent_cls.query_type
                    intent_cls.temporal_nature = llm_result.temporal_nature or "static"
                    intent_cls.requires_web = llm_result.requires_web
                    intent_cls.learnability = llm_result.learnability
                    intent_cls.entities = llm_result.entities or intent_cls.entities
                    intent_cls.method = "llm"
                    llm_edges = llm_result.graph_edges or []
                    if llm_result.temporal_nature == "realtime":
                        is_realtime = True
            except Exception as exc:
                log.debug(f"LLM intent enhancement failed: {exc}")

        # ── 3. Entity extraction + ambiguity resolution ────────────────────
        extracted = extract_entities(parsed)
        entities_raw = extracted.entities or intent_cls.entities or []
        entities_resolved = resolve_batch(entities_raw, parsed.content_tokens)
        entities = map_to_graph_concepts(entities_resolved)

        # Ensure source/target are in entities list
        for concept in filter(None, [intent_cls.source, intent_cls.target, intent_cls.concept]):
            norm = normalize_concept(concept)
            if norm and norm not in entities:
                entities.append(norm)

        # ── 4. Relation extraction ────────────────────────────────────────
        text_relations = extract_relations(parsed)

        # Add LLM-extracted edges as relations
        for edge in llm_edges:
            src = normalize_concept(str(edge.get("source", "")))
            tgt = normalize_concept(str(edge.get("target", "")))
            rel = str(edge.get("relation", "CORRELATES")).upper()
            if src and tgt:
                text_relations.append(Relation(source=src, relation=rel, target=tgt, confidence=0.7))

        # ── 5. Concept normalization ──────────────────────────────────────
        source = normalize_concept(intent_cls.source) if intent_cls.source else None
        target = normalize_concept(intent_cls.target) if intent_cls.target else None
        concept = normalize_concept(intent_cls.concept) if intent_cls.concept else None

        # ── 6. Semantic embedding ─────────────────────────────────────────
        semantic_vector = self._embedding_encoder.encode(parsed.content_tokens, parsed.normalized)

        # ── 7. Temporal detection ─────────────────────────────────────────
        token_set = set(parsed.tokens)
        is_temporal = bool(token_set & _TEMPORAL_KEYWORDS)
        temporal_nature = intent_cls.temporal_nature if hasattr(intent_cls, "temporal_nature") else (
            "realtime" if is_realtime else ("temporal" if is_temporal else "static")
        )

        temporal_data = TemporalData(
            is_temporal=is_temporal,
            temporal_nature=temporal_nature,
        )

        # ── 8. Analogy targets ────────────────────────────────────────────
        analogy_targets = []
        if intent_cls.reasoning_mode == "analogy" and source:
            analogy_targets = [source]

        # ── 9. Activation targets ─────────────────────────────────────────
        activation_targets = [e for e in [source, target, concept] if e]
        for e in entities[:3]:
            if e not in activation_targets:
                activation_targets.append(e)

        # ── 10. Context ───────────────────────────────────────────────────
        context = build_context(
            user_id=user_id,
            chat_id=chat_id,
            scope=scope,
            domain=domain,
            conversation_history=conversation_history,
            user_state=user_state,
            is_realtime=is_realtime,
        )

        return SemanticIR(
            intent=intent_cls.kind,
            reasoning_mode=intent_cls.reasoning_mode,
            entities=entities,
            relations=text_relations,
            constraints=[],
            context=context,
            confidence=intent_cls.confidence,
            learnability=intent_cls.learnability,
            temporal_data=temporal_data,
            analogy_targets=analogy_targets,
            activation_targets=activation_targets,
            raw_text=parsed.raw,
            normalized_text=parsed.normalized,
            source_concept=source,
            target_concept=target,
            personal_attribute=intent_cls.personal_attribute,
            personal_value=intent_cls.personal_value,
            semantic_vector=semantic_vector,
            query_type=intent_cls.query_type,
            requires_web=intent_cls.requires_web,
            requires_personal_graph=(intent_cls.kind in {"personal_fact", "personal_query"}),
            graph_edges=llm_edges,
        )


# Module-level convenience
def compile_to_ir(text: str, **kwargs: Any) -> SemanticIR:
    """Convenience function using a default SemanticCompiler."""
    return SemanticCompiler().compile(text, **kwargs)