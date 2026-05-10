"""encoder/entity_extractor.py — Extract named entities from parsed text.

Uses keyword-set heuristics from §3.2 of the Paragi paper (ported from OwnEncoder)
plus spaCy NER when available.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

from .parser import ParsedText

# Keyword sets from OwnEncoder (§3.2)
BIOLOGICAL_KEYWORDS: Set[str] = {
    "sleep", "hunger", "thirst", "tired", "pain", "breath", "body", "muscle", "health",
    "energy", "rest", "vital", "visceral", "organ", "heart", "brain", "nerve",
}
PSYCHOLOGICAL_KEYWORDS: Set[str] = {
    "happy", "sad", "fear", "anxiety", "mood", "think", "feel", "emotion", "mind",
    "memory", "will", "drive", "ego", "self", "desire", "mental", "focus",
}
SOCIAL_KEYWORDS: Set[str] = {
    "friend", "group", "family", "society", "rule", "law", "community", "other",
    "people", "person", "culture", "norm", "status", "role", "connect", "social",
}
INTELLECTUAL_KEYWORDS: Set[str] = {
    "logic", "reason", "fact", "learn", "study", "idea", "concept", "abstract",
    "knowledge", "system", "theory", "method", "complex", "simple", "skill",
}

# Try to load spaCy; fall back to keyword heuristics if unavailable
try:
    import spacy as _spacy  # type: ignore
    _nlp = _spacy.load("en_core_web_sm")
    _SPACY_AVAILABLE = True
except Exception:
    _nlp = None
    _SPACY_AVAILABLE = False


@dataclass
class ExtractedEntities:
    entities: List[str] = field(default_factory=list)
    noun_phrases: List[str] = field(default_factory=list)
    proper_nouns: List[str] = field(default_factory=list)
    semantic_categories: List[str] = field(default_factory=list)


def extract_entities(parsed: ParsedText) -> ExtractedEntities:
    """Extract entities from parsed text using spaCy NER + keyword heuristics."""
    result = ExtractedEntities()
    token_set = set(parsed.content_tokens)

    # Keyword-based semantic category detection
    if token_set & BIOLOGICAL_KEYWORDS:
        result.semantic_categories.append("biological")
    if token_set & PSYCHOLOGICAL_KEYWORDS:
        result.semantic_categories.append("psychological")
    if token_set & SOCIAL_KEYWORDS:
        result.semantic_categories.append("social")
    if token_set & INTELLECTUAL_KEYWORDS:
        result.semantic_categories.append("intellectual")

    if _SPACY_AVAILABLE and _nlp is not None:
        doc = _nlp(parsed.normalized)
        for ent in doc.ents:
            label = ent.text.strip().lower()
            if label and label not in result.entities:
                result.entities.append(label)
                if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "FAC", "PRODUCT"):
                    result.proper_nouns.append(label)
        for chunk in doc.noun_chunks:
            phrase = chunk.text.strip().lower()
            if phrase and phrase not in result.noun_phrases:
                result.noun_phrases.append(phrase)
    else:
        # Heuristic: content tokens > 2 chars that aren't question words
        from .tokenizer import STOP_WORDS
        _question_words = {"what", "why", "how", "when", "where", "who", "which", "is", "are"}
        for token in parsed.content_tokens:
            if len(token) > 2 and token not in _question_words and token not in STOP_WORDS:
                if token not in result.entities:
                    result.entities.append(token)

    return result
