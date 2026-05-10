"""
encoder/semantic_encoder.py — Orchestrate text-to-SemanticIR conversion.
"""
from __future__ import annotations

from typing import List, Dict, Any
from core.semantic_ir import SemanticIR
from core.logger import get_logger
from .parser import parse, ParsedText
from .entity_extractor import extract_entities
from .relation_extractor import extract_relations
from .intent_classifier import classify

log = get_logger(__name__)


class SemanticEncoder:
    """
    Coordinates extraction and classification to produce a SemanticIR.
    """

    def encode(self, text: str) -> SemanticIR:
        """Process raw text into SemanticIR."""
        log.info(f"Encoding text: {text}")
        
        # 1. Parse text
        parsed = parse(text)
        
        # 2. Extract entities
        extracted_entities = extract_entities(parsed)
        
        # 3. Extract relations
        relations = extract_relations(parsed)
        
        # 4. Classify intent
        intent_info = classify(parsed)
        
        # 5. Build SemanticIR
        # Ensure relation participants are anchored as concepts
        relation_concepts = []
        for rel in relations:
            relation_concepts.extend([rel.source, rel.target])
            
        ir = SemanticIR(
            text=parsed.raw,
            tokens=parsed.tokens,
            entities=extracted_entities.entities,
            concepts=list(set(extracted_entities.noun_phrases + relation_concepts)),
            relations=relations,
            intent=intent_info.kind,
            confidence=intent_info.confidence,
            metadata={
                "reasoning_mode": intent_info.mode.value,
                "proper_nouns": extracted_entities.proper_nouns,
                "categories": extracted_entities.semantic_categories
            }
        )
        
        # 6. Extract markers (temporal/causal)
        # Placeholder for specialized markers extraction
        
        return ir
