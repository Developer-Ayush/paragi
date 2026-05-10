"""reasoning/analogy_reasoner.py — Analogy reasoning via structural graph similarity."""
from __future__ import annotations
from core.semantic_ir import SemanticIR
from graph.graph import GraphEngine
from graph.analogy import find_analogies, find_shared_ancestors


def analogy_reason(graph: GraphEngine, ir: SemanticIR, concept: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    candidates = find_analogies(graph, concept, limit=5, min_shared=2)
    ancestors = find_shared_ancestors(graph, concept, candidates[0].candidate_label) if candidates else []

    if not candidates:
        return ReasoningResult(answer="", confidence=0.0, node_path=[concept],
                               mode="analogy", used_fallback=True)

    top = candidates[0]
    shared = ", ".join(top.shared_neighbors[:3])
    answer = f"{concept} is analogous to {top.candidate_label} (shared: {shared})"
    if ancestors:
        answer += f". Both are types of: {', '.join(ancestors[:2])}"

    return ReasoningResult(
        answer=answer, confidence=min(0.9, top.jaccard + 0.3),
        node_path=[concept, top.candidate_label], mode="analogy",
        extra={"candidates": [(c.candidate_label, c.jaccard) for c in candidates[:3]]},
    )
