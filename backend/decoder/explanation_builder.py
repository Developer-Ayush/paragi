"""decoder/explanation_builder.py — Build human-readable reasoning path explanations."""
from __future__ import annotations
from typing import List
from core.constants import EDGE_RELATION_TEXT


def build_explanation(node_path: List[str], edge_types: List[str], *, max_steps: int = 5) -> str:
    """Build a step-by-step explanation of the reasoning path."""
    if not node_path or len(node_path) < 2:
        return ""
    lines = ["Reasoning path:"]
    for i in range(min(len(node_path) - 1, len(edge_types), max_steps)):
        src, tgt = node_path[i], node_path[i + 1]
        rel = EDGE_RELATION_TEXT.get(edge_types[i], "→")
        lines.append(f"  {i+1}. {src} {rel} {tgt}")
    return "\n".join(lines)
