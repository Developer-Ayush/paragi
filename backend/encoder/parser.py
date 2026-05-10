"""encoder/parser.py — Text parsing: normalization, sentence splitting, token extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .tokenizer import normalize_text, tokenize, tokenize_filtered


@dataclass
class ParsedText:
    """Result of the initial text parsing stage."""
    raw: str
    normalized: str
    tokens: List[str]               # all tokens
    content_tokens: List[str]       # stop-words removed
    sentences: List[str]
    word_count: int
    is_question: bool
    question_word: str              # what/why/how/when/where/who or ""


_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+\s+")
_QUESTION_WORDS = {"what", "why", "how", "when", "where", "who", "which", "whose"}


def parse(text: str) -> ParsedText:
    """Parse raw user text into structured form."""
    raw = text.strip()
    normalized = normalize_text(raw)
    tokens = tokenize(normalized)
    content_tokens = tokenize_filtered(normalized)
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(normalized) if s.strip()]
    if not sentences:
        sentences = [normalized]

    is_question = normalized.endswith("?") or (bool(tokens) and tokens[0] in _QUESTION_WORDS)
    question_word = tokens[0] if tokens and tokens[0] in _QUESTION_WORDS else ""

    return ParsedText(
        raw=raw,
        normalized=normalized,
        tokens=tokens,
        content_tokens=content_tokens,
        sentences=sentences,
        word_count=len(tokens),
        is_question=is_question,
        question_word=question_word,
    )
