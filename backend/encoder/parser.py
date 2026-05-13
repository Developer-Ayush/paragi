"""encoder/parser.py"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class ParsedText:
    raw: str
    tokens: List[str] = field(default_factory=list)

def parse(text: str) -> ParsedText:
    return ParsedText(raw=text, tokens=text.split())
