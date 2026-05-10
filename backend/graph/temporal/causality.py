"""graph/temporal/causality.py — Causality chain extraction from CAUSES + TEMPORAL edges."""
from __future__ import annotations
from typing import List
from graph.graph import GraphEngine, PathMatch


def causal_temporal_chain(
    graph: GraphEngine, source: str, target: str, *, max_hops: int = 7,
) -> List[PathMatch]:
    """Extract paths using both CAUSES and TEMPORAL edges for causal-temporal reasoning."""
    return graph.find_paths(
        source, target,
        max_hops=max_hops,
        edge_type_filter=["CAUSES", "TEMPORAL", "SEQUENCE", "CORRELATES"],
    )


def direct_cause(graph: GraphEngine, source: str, target: str) -> bool:
    """Return True if a direct CAUSES edge exists from source to target."""
    edge = graph.get_edge(source, target)
    return edge is not None and edge.type == "CAUSES"
