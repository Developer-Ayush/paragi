"""graph/contradiction/resolver.py — Contradiction resolution strategies."""
from __future__ import annotations
from graph.graph import GraphEngine, ContradictionResult


def resolve_by_weakening(result: ContradictionResult, graph: GraphEngine) -> str:
    """Weaken the minority edge and return a resolution summary."""
    if result.minority_edge_weakened:
        return f"Weakened minority claim. Dominant: '{result.verdict}' ({result.confidence:.2f})"
    return f"No resolution needed. Verdict: '{result.verdict}'"


def resolve_by_flagging(result: ContradictionResult) -> dict:
    """Flag contradiction for human review."""
    return {
        "status": "flagged",
        "source": result.source_label,
        "conflict": [result.positive_target, result.negative_target],
        "confidence": result.confidence,
        "verdict": result.verdict,
    }
