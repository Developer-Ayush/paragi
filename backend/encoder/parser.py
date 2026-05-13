"""encoder/parser.py"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class ParsedText:
    raw: str
    normalized: str = ""
    tokens: List[str] = field(default_factory=list)
    content_tokens: List[str] = field(default_factory=list)
    is_question: bool = False

def parse(text: str) -> ParsedText:
    tokens = text.split()
    is_question = text.strip().endswith("?")
    return ParsedText(
        raw=text,
        normalized=text.lower(),
        tokens=tokens,
        content_tokens=tokens,
        is_question=is_question
    )
