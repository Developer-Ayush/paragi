"""
encoder/relation_extractor.py — Extract semantic relations from parsed text.

Uses spaCy dependency parsing when available, with regex fallback.
Relations are mapped to EdgeType values for direct graph insertion.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
from core.semantic_ir import IRRelation
from core.enums import EdgeType
from .parser import ParsedText

# spaCy optional
try:
    import spacy as _spacy
    _nlp = _spacy.load("en_core_web_sm")
    _SPACY_AVAILABLE = True
except Exception:
    _nlp = None
    _SPACY_AVAILABLE = False

# Verb → EdgeType mapping
_VERB_EDGE_MAP: dict[str, EdgeType] = {
    "cause":   EdgeType.CAUSES,
    "causes":  EdgeType.CAUSES,
    "caused":  EdgeType.CAUSES,
    "lead":    EdgeType.CAUSES,
    "leads":   EdgeType.CAUSES,
    "result":  EdgeType.CAUSES,
    "create":  EdgeType.CAUSES,
    "produce": EdgeType.CAUSES,
    "is":      EdgeType.IS_A,
    "are":     EdgeType.IS_A,
    "was":     EdgeType.IS_A,
    "contain": EdgeType.PART_OF,
    "include": EdgeType.PART_OF,
    "follow":  EdgeType.TEMPORAL,
    "precede": EdgeType.TEMPORAL,
    "resemble": EdgeType.SIMILARITY,
    "similar": EdgeType.SIMILARITY,
    "like":    EdgeType.ANALOGY,
    "depend":  EdgeType.DEPENDS_ON,
    "require": EdgeType.DEPENDS_ON,
    "need":    EdgeType.DEPENDS_ON,
}


def extract_relations(parsed: ParsedText) -> List[IRRelation]:
    """Extract subject-verb-object relations from text."""
    relations: List[IRRelation] = []

    if _SPACY_AVAILABLE and _nlp is not None:
        relations.extend(_extract_via_spacy(parsed.normalized))
    
    if not relations:
        relations.extend(_extract_via_heuristic(parsed))

    return relations


def _extract_via_spacy(text: str) -> List[IRRelation]:
    """Use spaCy dependency parse to extract SVO triples."""
    relations: List[IRRelation] = []
    doc = _nlp(text)

    for token in doc:
        if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
            source = token.text.strip().lower()
            verb_lemma = token.head.lemma_.lower()
            edge_type = _VERB_EDGE_MAP.get(verb_lemma, EdgeType.ASSOCIATED_WITH)

            for child in token.head.children:
                if child.dep_ in ("dobj", "attr", "acomp", "pobj"):
                    target = child.text.strip().lower()
                    if source and target and source != target:
                        relations.append(IRRelation(
                            source=source,
                            relation=edge_type,
                            target=target,
                            confidence=0.75,
                        ))
    return relations


def _extract_via_heuristic(parsed: ParsedText) -> List[IRRelation]:
    """Regex / pattern heuristic relation extraction fallback."""
    import re
    relations: List[IRRelation] = []
    text = parsed.normalized

    # Pattern: "X causes Y"
    causal = re.findall(r"([\w\s]+?)\s+(?:causes?|leads?\s+to|results?\s+in)\s+([\w\s]+)", text)
    for src, tgt in causal:
        relations.append(IRRelation(source=src.strip(), relation=EdgeType.CAUSES, target=tgt.strip(), confidence=0.8))

    # Pattern: "X is Y"
    is_a = re.findall(r"([\w\s]+?)\s+is\s+(?:a|an|the)?\s*([\w\s]+)", text)
    for src, tgt in is_a:
        relations.append(IRRelation(source=src.strip(), relation=EdgeType.IS_A, target=tgt.strip(), confidence=0.7))

    return relations
