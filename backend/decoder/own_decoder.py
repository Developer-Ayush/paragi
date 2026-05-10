"""decoder/own_decoder.py — Template-based decoder when LLM is disabled.

Ported from app/own_decoder.py. Converts graph reasoning results into
human-readable sentences using template patterns.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from core.constants import EDGE_RELATION_TEXT, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM
from core.logger import get_logger

log = get_logger(__name__)

_TEMPLATES: Dict[str, List[str]] = {
    "CAUSES": [
        "{source} causes {target}.",
        "{source} leads to {target}.",
        "{target} is caused by {source}.",
    ],
    "IS_A": [
        "{source} is a type of {target}.",
        "{source} is classified as {target}.",
    ],
    "CORRELATES": [
        "{source} is related to {target}.",
        "{source} is associated with {target}.",
    ],
    "TEMPORAL": [
        "{source} typically happens before {target}.",
        "{source} precedes {target}.",
    ],
    "ANALOGY": [
        "{source} is analogous to {target}.",
        "{source} is structurally similar to {target}.",
    ],
    "PART_OF": [
        "{source} is part of {target}.",
        "{source} is a component of {target}.",
    ],
    "CONTRADICTS": [
        "{source} contradicts {target}.",
        "{source} conflicts with {target}.",
    ],
    "default": [
        "{source} is connected to {target}.",
        "{source} relates to {target}.",
    ],
}

_UNCERTAINTY_PHRASES = [
    "I'm not entirely sure, but ",
    "Based on limited information: ",
    "This is uncertain, but ",
]


class OwnDecoder:
    """
    Template-based decoder: converts graph state → natural language.
    No LLM required. Used as fallback or standalone decoder.
    """

    def __init__(self, *, model_path: Optional[Path] = None) -> None:
        self.model_path = model_path
        # Could load learned template weights from model_path in future

    def decode(
        self,
        answer: str,
        confidence: float,
        node_path: List[str],
        edge_type: str = "CORRELATES",
    ) -> str:
        """
        Format an answer string with confidence adjustments.
        """
        if not answer:
            return ""

        # Strip very low confidence
        if confidence < 0.12:
            return ""

        result = answer.strip()

        # Add uncertainty prefix for low confidence
        if confidence < CONFIDENCE_MEDIUM:
            result = _UNCERTAINTY_PHRASES[0] + result[0].lower() + result[1:]

        # Ensure sentence ends with punctuation
        if result and result[-1] not in ".!?":
            result += "."

        return result

    def decode_from_path(
        self,
        node_path: List[str],
        edge_types: List[str],
        confidence: float,
    ) -> str:
        """Generate a sentence from a node path and edge types."""
        if not node_path or len(node_path) < 2:
            return ""

        parts = []
        for i in range(min(len(node_path) - 1, len(edge_types))):
            src = node_path[i]
            tgt = node_path[i + 1]
            etype = edge_types[i] if i < len(edge_types) else "CORRELATES"
            rel_text = EDGE_RELATION_TEXT.get(etype, "is related to")
            parts.append(f"{src} {rel_text} {tgt}")

        result = "; ".join(parts) + "."
        return self.decode(result, confidence, node_path)

    def template_sentence(self, source: str, target: str, edge_type: str) -> str:
        """Generate a single sentence from a source-target-edge triple."""
        templates = _TEMPLATES.get(edge_type, _TEMPLATES["default"])
        template = templates[0]
        return template.format(source=source, target=target)

    def train_from_records(self, records: list) -> None:
        """Placeholder: train template weights from (input, output) pairs."""
        log.info(f"OwnDecoder: {len(records)} training records (stub)")
