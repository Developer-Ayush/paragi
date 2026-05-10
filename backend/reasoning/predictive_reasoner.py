"""reasoning/predictive_reasoner.py — Predictive reasoning by following causal chains forward."""
from __future__ import annotations
from core.semantic_ir import SemanticIR
from graph.graph import GraphEngine


def predictive_reason(graph: GraphEngine, ir: SemanticIR, source: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    node = graph.get_node_by_label(source)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="predictive", used_fallback=True)

    # Follow CAUSES edges forward up to 4 hops
    chain = [source]
    visited = {node.id}
    current_id = node.id
    for _ in range(4):
        edges = [e for e in graph.store.list_outgoing(current_id)
                 if e.type in ("CAUSES",) and e.target not in visited]
        if not edges:
            break
        best = max(edges, key=lambda e: e.strength)
        next_label = graph.get_node_label(best.target)
        chain.append(next_label)
        visited.add(best.target)
        current_id = best.target

    if len(chain) <= 1:
        return ReasoningResult(answer="", confidence=0.0, mode="predictive", used_fallback=True)

    answer = " → ".join(chain)
    return ReasoningResult(
        answer=f"If {source} occurs: {answer}",
        confidence=0.6, node_path=chain, mode="predictive",
    )
