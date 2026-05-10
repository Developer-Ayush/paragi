"""reasoning/abstraction_reasoner.py — Abstract category reasoning via IS_A/ABSTRACTS_TO."""
from __future__ import annotations
from core.semantic_ir import SemanticIR
from graph.graph import GraphEngine
from graph.traversal.constrained import abstraction_paths


def abstraction_reason(graph: GraphEngine, ir: SemanticIR, concept: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    # Walk IS_A / ABSTRACTS_TO edges upward to find categories
    node = graph.get_node_by_label(concept)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="abstraction", used_fallback=True)

    categories = []
    visited = {node.id}
    queue = [node.id]
    for _ in range(5):
        next_queue = []
        for nid in queue:
            for edge in graph.store.list_outgoing(nid):
                if edge.type in ("IS_A", "ABSTRACTS_TO") and edge.target not in visited:
                    visited.add(edge.target)
                    categories.append(graph.get_node_label(edge.target))
                    next_queue.append(edge.target)
        queue = next_queue
        if not queue:
            break

    if not categories:
        return ReasoningResult(answer="", confidence=0.0, mode="abstraction", used_fallback=True)

    answer = f"{concept} is a type of {', '.join(categories[:3])}"
    return ReasoningResult(
        answer=answer, confidence=0.7, node_path=[concept] + categories[:3],
        mode="abstraction", extra={"categories": categories},
    )
