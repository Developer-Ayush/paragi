"""reasoning/contradiction_reasoner.py — Contradiction detection and structural resolution."""
from __future__ import annotations

from typing import List, Optional
from graph.graph import GraphEngine, ContradictionResult
from core.semantic_ir import SemanticIR
from .engine import ReasoningResult


def contradiction_reason(graph: GraphEngine, ir: SemanticIR, source: str, positive_target: str, negative_target: Optional[str] = None) -> ReasoningResult:
    """
    Analyzes conflicting evidence for a concept.
    Uses structural 'voting' across the graph to determine which side of a contradiction has more support.
    """
    if not negative_target:
        # Try to find a contradictory node in the graph
        neighbors = graph.get_neighbors(source)
        contradictors = [graph.get_node_label(e.target) for e in neighbors if e.type == "CONTRADICTS"]
        negative_target = contradictors[0] if contradictors else f"not {positive_target}"

    # Use the graph's built-in contradiction voting logic
    vote = graph.contradiction_vote(source, positive_target, negative_target)
    
    answer = (
        f"Contradiction Analysis for '{source}': The verdict is '{vote.verdict}'. "
        f"Structural support: {vote.positive_paths} positive paths vs {vote.negative_paths} negative paths. "
        f"Resolution Confidence: {vote.confidence:.2%}"
    )
    
    if vote.minority_edge_weakened:
        answer += " (Note: Minority evidence has been weakened via Hebbian suppression.)"

    return ReasoningResult(
        answer=answer,
        confidence=vote.confidence,
        node_path=[source, positive_target, negative_target],
        mode="contradiction",
        extra={
            "pos_count": vote.positive_paths,
            "neg_count": vote.negative_paths,
            "verdict": vote.verdict
        }
    )
