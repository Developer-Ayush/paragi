"""graph/contradiction/detector.py — Contradiction detection in the graph."""
from __future__ import annotations
from typing import List, Tuple
from graph.graph import GraphEngine, ContradictionResult


def detect_contradiction(
    graph: GraphEngine, source: str, pos_target: str, neg_target: str, **kwargs
) -> ContradictionResult:
    """Detect and vote on a contradiction between two competing claims."""
    return graph.contradiction_vote(source, pos_target, neg_target, **kwargs)


def scan_contradictions(
    graph: GraphEngine, *, max_pairs: int = 50,
) -> List[Tuple[str, str, str]]:
    """
    Scan the graph for potential CONTRADICTS edges.
    Returns list of (source, target_a, target_b) candidates.
    """
    candidates: List[Tuple[str, str, str]] = []
    checked = set()
    for edge_id in graph.store.list_edge_ids():
        edge = graph.store.get_edge(edge_id)
        if edge is None or edge.type != "CONTRADICTS":
            continue
        key = (edge.source, edge.target)
        if key not in checked:
            checked.add(key)
            source_label = graph.get_node_label(edge.source)
            target_label = graph.get_node_label(edge.target)
            candidates.append((source_label, target_label, "CONTRADICTS"))
        if len(candidates) >= max_pairs:
            break
    return candidates
