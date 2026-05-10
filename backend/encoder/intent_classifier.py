"""encoder/intent_classifier.py — Classify user intent and extract structured fields."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .parser import ParsedText


@dataclass
class IntentClassification:
    kind: str
    source: Optional[str] = None
    target: Optional[str] = None
    concept: Optional[str] = None
    personal_attribute: Optional[str] = None
    personal_value: Optional[str] = None
    reasoning_mode: str = "general"
    query_type: str = "STATIC_KNOWLEDGE"
    temporal_nature: str = "static"
    requires_web: bool = False
    learnability: float = 0.0
    entities: List[str] = field(default_factory=list)
    graph_edges: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.8
    method: str = "regex"


_RELATION_PATTERNS = [
    re.compile(r"^\s*(?:does|can|could|will)\s+([a-z0-9_]+)\s+([a-z0-9_]+)\??\s*$"),
    re.compile(r"^\s*is\s+([a-z0-9_]+)\s+([a-z0-9_]+)\??\s*$"),
]
_CONCEPT_PATTERNS = [
    re.compile(r"^\s*what\s+(?:is|are)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*who\s+(?:is|was|are)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*(?:define|describe|explain)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*tell\s+me\s+about\s+(.+?)\??\s*$"),
    re.compile(r"^\s*how\s+(?:much|many|big|old|tall|fast|far|long)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*how\s+(?:do|does|did|is|are|was|were|can|could)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*where\s+(?:is|are|was|were|do|does|did|can)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*when\s+(?:is|are|was|were|do|does|did|will)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*why\s+(?:is|are|do|does|did|was|were|can)\s+(.+?)\??\s*$"),
    re.compile(r"^\s*(.+?\s+of\s+.+?)\??\s*$"),
]
_GENERAL_FACT_PATTERN = re.compile(r"^\s*(.+?)\s+is\s+(.+?)\s*$")
_PERSONAL_PATTERNS = [
    (re.compile(r"^\s*my\s+name\s+is\s+([a-z0-9_ ]+)\s*$"), "name"),
    (re.compile(r"^\s*my\s+nationality\s+is\s+([a-z0-9_ ]+)\s*$"), "nationality"),
    (re.compile(r"^\s*i\s+am\s+from\s+([a-z0-9_ ]+)\s*$"), "nationality"),
    (re.compile(r"^\s*i\s+am\s+([a-z0-9_ ]+)\s*$"), "name"),
    (re.compile(r"^\s*i\s+live\s+in\s+([a-z0-9_ ]+)\s*$"), "location"),
    (re.compile(r"^\s*i\s+like\s+([a-z0-9_ ]+)\s*$"), "preference"),
]
_PERSONAL_FACT_GENERIC = re.compile(r"^\s*my\s+([a-z0-9_ ]{1,80}?)\s+is\s+([a-z0-9_ ]+)\s*$")
_PERSONAL_QUERY_PATTERNS = [
    (re.compile(r"^\s*what\s+is\s+my\s+name\??\s*$"), "name"),
    (re.compile(r"^\s*what\s+is\s+my\s+nationality\??\s*$"), "nationality"),
    (re.compile(r"^\s*where\s+am\s+i\s+from\??\s*$"), "nationality"),
    (re.compile(r"^\s*who\s+am\s+i\??\s*$"), "identity"),
    (re.compile(r"^\s*where\s+do\s+i\s+live\??\s*$"), "location"),
    (re.compile(r"^\s*what\s+do\s+i\s+like\??\s*$"), "preference"),
]
_PERSONAL_QUERY_GENERIC = re.compile(r"^\s*what\s+is\s+my\s+([a-z0-9_ ]+)\??\s*$")
_GREETING_WORDS = {"hi", "hello", "hey", "greetings", "howdy", "sup", "yo", "hiya"}
_REALTIME_KEYWORDS = {
    "news", "today", "current", "latest", "now", "weather", "stock",
    "price", "live", "breaking", "recent", "2024", "2025", "2026",
    "who is", "who was",
}


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def classify(parsed: ParsedText) -> IntentClassification:
    """Classify intent using compiled regex patterns. No LLM required."""
    text = parsed.normalized

    if text in _GREETING_WORDS or (len(parsed.tokens) <= 2 and set(parsed.tokens) & _GREETING_WORDS):
        return IntentClassification(kind="greeting")

    for pattern, attribute in _PERSONAL_PATTERNS:
        m = pattern.match(text)
        if m:
            value = _norm(m.group(1))
            if value:
                return IntentClassification(
                    kind="personal_fact", personal_attribute=attribute,
                    personal_value=value, query_type="PERSONAL_MEMORY", learnability=1.0,
                )

    m = _PERSONAL_FACT_GENERIC.match(text)
    if m:
        attr, val = _norm(m.group(1)), _norm(m.group(2))
        if attr and val:
            return IntentClassification(
                kind="personal_fact", personal_attribute=attr,
                personal_value=val, query_type="PERSONAL_MEMORY", learnability=1.0,
            )

    for pattern, attribute in _PERSONAL_QUERY_PATTERNS:
        if pattern.match(text):
            return IntentClassification(kind="personal_query", personal_attribute=attribute, query_type="PERSONAL_MEMORY")

    m = _PERSONAL_QUERY_GENERIC.match(text)
    if m:
        attr = _norm(m.group(1))
        if attr:
            return IntentClassification(kind="personal_query", personal_attribute=attr, query_type="PERSONAL_MEMORY")

    for pattern in _RELATION_PATTERNS:
        m = pattern.match(text)
        if m:
            src, tgt = _norm(m.group(1)), _norm(m.group(2))
            mode = _infer_mode(text)
            qt = "CAUSAL_REASONING" if mode == "causal" else "STATIC_KNOWLEDGE"
            rel = "CAUSES" if mode == "causal" else "CORRELATES"
            return IntentClassification(
                kind="relation", source=src, target=tgt, reasoning_mode=mode, 
                query_type=qt, learnability=0.8,
                graph_edges=[{"source": src, "target": tgt, "relation": rel}]
            )

    for pattern in _CONCEPT_PATTERNS:
        m = pattern.match(text)
        if m:
            concept = _norm(m.group(1))
            if concept:
                rw = any(k in text for k in _REALTIME_KEYWORDS) or bool(set(parsed.tokens) & _REALTIME_KEYWORDS)
                qt = "REALTIME_KNOWLEDGE" if rw else "STATIC_KNOWLEDGE"
                return IntentClassification(kind="concept", concept=concept, query_type=qt, requires_web=rw, learnability=0.8, entities=[concept])

    m = _GENERAL_FACT_PATTERN.match(text)
    if m:
        subject, obj = _norm(m.group(1)), _norm(m.group(2))
        skip = {"what", "who", "where", "when", "why", "how", "which"}
        if subject and obj and subject not in skip:
            return IntentClassification(
                kind="general_fact", source=subject, target=obj,
                learnability=0.8,
                graph_edges=[{"source": subject, "target": obj, "relation": "CORRELATES"}],
            )

    return IntentClassification(kind="unknown")


def _infer_mode(text: str) -> str:
    t = text.lower()
    if "why" in t or "cause" in t or "because" in t:
        return "causal"
    if "before" in t or "after" in t or "when" in t:
        return "temporal"
    if "similar" in t or "like" in t or "analogy" in t:
        return "analogy"
    return "general"
