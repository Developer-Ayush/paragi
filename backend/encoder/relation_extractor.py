"""encoder/relation_extractor.py — Extract semantic relations from parsed text.

Uses spaCy dependency parsing when available, with regex fallback.
Relations are mapped to EdgeType values for direct graph insertion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.semantic_ir import Relation
from .parser import ParsedText

# spaCy optional
try:
    import spacy as _spacy  # type: ignore
    _nlp = _spacy.load("en_core_web_sm")
    _SPACY_AVAILABLE = True
except Exception:
    _nlp = None
    _SPACY_AVAILABLE = False

# Verb → EdgeType mapping for dependency-based extraction
_VERB_EDGE_MAP: dict[str, str] = {
    "cause":   "CAUSES",
    "causes":  "CAUSES",
    "caused":  "CAUSES",
    "lead":    "CAUSES",
    "leads":   "CAUSES",
    "result":  "CAUSES",
    "create":  "CAUSES",
    "produce": "CAUSES",
    "is":      "IS_A",
    "are":     "IS_A",
    "was":     "IS_A",
    "contain": "PART_OF",
    "include": "PART_OF",
    "follow":  "TEMPORAL",
    "precede": "TEMPORAL",
    "resemble":"SIMILARITY",
    "similar": "SIMILARITY",
    "like":    "ANALOGY",
    "depend":  "DEPENDS_ON",
    "require": "DEPENDS_ON",
    "need":    "DEPENDS_ON",
}


def extract_relations(parsed: ParsedText) -> List[Relation]:
    """Extract subject-verb-object relations from text."""
    relations: List[Relation] = []

    if _SPACY_AVAILABLE and _nlp is not None:
        relations.extend(_extract_via_spacy(parsed.normalized))
    
    if not relations:
        relations.extend(_extract_via_heuristic(parsed))

    return relations


def _extract_via_spacy(text: str) -> List[Relation]:
    """Use spaCy dependency parse to extract SVO triples."""
    relations: List[Relation] = []
    doc = _nlp(text)

    for token in doc:
        if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
            source = token.text.strip().lower()
            verb_lemma = token.head.lemma_.lower()
            edge_type = _VERB_EDGE_MAP.get(verb_lemma, "CORRELATES")

            for child in token.head.children:
                if child.dep_ in ("dobj", "attr", "acomp", "pobj"):
                    target = child.text.strip().lower()
                    if source and target and source != target:
                        relations.append(Relation(
                            source=source,
                            relation=edge_type,
                            target=target,
                            confidence=0.75,
                        ))
    return relations


def _extract_via_heuristic(parsed: ParsedText) -> List[Relation]:
    """Regex / pattern heuristic relation extraction fallback."""
    import re
    relations: List[Relation] = []
    text = parsed.normalized

    # Pattern: "X causes Y" / "X leads to Y"
    causal = re.findall(r"(\w+)\s+(?:causes?|leads?\s+to|results?\s+in)\s+(\w+)", text)
    for src, tgt in causal:
        relations.append(Relation(source=src, relation="CAUSES", target=tgt, confidence=0.8))

    # Pattern: "X is a Y"
    is_a = re.findall(r"(\w+)\s+is\s+(?:a|an)\s+(\w+)", text)
    for src, tgt in is_a:
        relations.append(Relation(source=src, relation="IS_A", target=tgt, confidence=0.7))

    # Pattern: "X is part of Y"
    part_of = re.findall(r"(\w+)\s+is\s+part\s+of\s+(\w+)", text)
    for src, tgt in part_of:
        relations.append(Relation(source=src, relation="PART_OF", target=tgt, confidence=0.7))

    # Pattern: "X is similar to Y" / "X is like Y"
    similar = re.findall(r"(\w+)\s+(?:is\s+similar\s+to|is\s+like)\s+(\w+)", text)
    for src, tgt in similar:
        relations.append(Relation(source=src, relation="SIMILARITY", target=tgt, confidence=0.65))

    return relations
