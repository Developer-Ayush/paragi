"""utils/text.py — Text normalization utilities."""
from core.types import normalize_label, normalize_label_raw
import re

_WHITESPACE = re.compile(r"\s+")

def clean_text(text: str) -> str:
    return _WHITESPACE.sub(" ", text.strip().lower())

def sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]

__all__ = ["normalize_label", "normalize_label_raw", "clean_text", "sentence_case"]
