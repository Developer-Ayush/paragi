"""
encoder/intent_classifier.py — Classify user intent and extract structured fields.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.enums import ReasoningMode
from .parser import ParsedText


@dataclass
class IntentClassification:
    kind: str
    mode: ReasoningMode = ReasoningMode.GENERAL
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


_GREETING_WORDS = {"hi", "hello", "hey", "greetings", "howdy", "sup", "yo", "hiya"}
_CAUSAL_KEYWORDS = {"why", "cause", "because", "lead to", "result in"}
_TEMPORAL_KEYWORDS = {"when", "before", "after", "while", "during", "sequence"}
_ANALOGY_KEYWORDS = {"similar", "like", "analogy", "comparable"}


def classify(parsed: ParsedText) -> IntentClassification:
    """Classify intent using heuristic patterns."""
    text = parsed.normalized
    tokens = set(parsed.tokens)

    # 1. Greeting
    if text in _GREETING_WORDS or (tokens & _GREETING_WORDS):
        return IntentClassification(kind="greeting", mode=ReasoningMode.GENERAL, confidence=1.0)

    # 2. Infer Reasoning Mode
    mode = ReasoningMode.GENERAL
    confidence = 0.5
    
    if any(k in text for k in _CAUSAL_KEYWORDS):
        mode = ReasoningMode.CAUSAL
        confidence = 0.8
    elif any(k in text for k in _TEMPORAL_KEYWORDS):
        mode = ReasoningMode.TEMPORAL
        confidence = 0.8
    elif any(k in text for k in _ANALOGY_KEYWORDS):
        mode = ReasoningMode.ANALOGY
        confidence = 0.8
    elif "is" in text and ("part of" in text or "type of" in text):
        mode = ReasoningMode.ABSTRACTION
        confidence = 0.7
        
    # 3. Personal Intent (§6.2)
    kind = "query" if parsed.is_question else "assertion"
    if "my" in tokens or "i " in text or "i'm" in text:
        kind = "personal_fact" if not parsed.is_question else "personal_query"
        confidence = 0.9

    return IntentClassification(
        kind=kind,
        mode=mode,
        confidence=confidence
    )
