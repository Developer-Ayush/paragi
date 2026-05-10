"""graph/temporal/sequence.py — TEMPORAL edge traversal and sequence reasoning."""
from __future__ import annotations
from typing import List
from graph.graph import GraphEngine, PathMatch
from graph.traversal.constrained import temporal_paths


def get_sequence(graph: GraphEngine, start: str, end: str, **kwargs) -> List[PathMatch]:
    """Find temporal sequences from start to end via TEMPORAL/SEQUENCE edges."""
    return temporal_paths(graph, start, end, **kwargs)


def get_temporal_neighbors(graph: GraphEngine, label: str) -> List[str]:
    """Get all concepts directly connected via TEMPORAL or SEQUENCE edges."""
    node = graph.get_node_by_label(label)
    if node is None:
        return []
    return [
        graph.get_node_label(e.target)
        for e in graph.store.list_outgoing(node.id)
        if e.type in ("TEMPORAL", "SEQUENCE")
    ]
