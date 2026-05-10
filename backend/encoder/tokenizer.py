"""encoder/tokenizer.py — Low-level tokenization and text normalization."""
from __future__ import annotations

import re
from typing import List

# Match word tokens: lowercase letters, digits, underscores
TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Common stop words to filter for semantic processing
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "this", "that", "these", "those", "i", "me", "my", "you", "your",
    "it", "its", "we", "our", "they", "their", "what", "which", "who",
    "and", "or", "but", "if", "then", "so", "yet", "nor",
})


def tokenize(text: str) -> List[str]:
    """Extract all word tokens from normalized text."""
    return TOKEN_RE.findall(text.strip().lower())


def tokenize_filtered(text: str, *, remove_stopwords: bool = True) -> List[str]:
    """Extract tokens and optionally remove stop words."""
    tokens = tokenize(text)
    if remove_stopwords:
        return [t for t in tokens if t not in STOP_WORDS and len(t) > 2]
    return tokens


def normalize_text(text: str) -> str:
    """Lowercase + collapse whitespace."""
    return " ".join(text.strip().lower().split())


def is_stop_word(token: str) -> bool:
    return token in STOP_WORDS
