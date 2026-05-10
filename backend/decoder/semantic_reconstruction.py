"""decoder/semantic_reconstruction.py — Reconstruct semantic content from GraphIR."""
from __future__ import annotations
from typing import List
from core.constants import EDGE_RELATION_TEXT
from .graph_to_ir import GraphIR


def reconstruct(gir: GraphIR) -> str:
    """Convert GraphIR fact triples into a structured natural-language answer."""
    if not gir.fact_triples:
        return ""
    parts = []
    for src, etype, tgt in gir.fact_triples[:5]:
        rel_text = EDGE_RELATION_TEXT.get(etype, "is related to")
        parts.append(f"{src} {rel_text} {tgt}")
    return ". ".join(parts) + "." if parts else ""


def reconstruct_from_path(node_path: List[str], edge_types: List[str]) -> str:
    """Reconstruct from a traversal path."""
    parts = []
    for i in range(min(len(node_path) - 1, len(edge_types))):
        rel = EDGE_RELATION_TEXT.get(edge_types[i], "relates to")
        parts.append(f"{node_path[i]} {rel} {node_path[i+1]}")
    return ". ".join(parts) + "." if parts else ""
