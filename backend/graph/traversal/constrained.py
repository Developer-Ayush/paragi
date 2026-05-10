"""
graph/traversal/constrained.py — Traversal with semantic constraints.
"""
from __future__ import annotations

from typing import List, Set, Optional, Iterable
from core.enums import EdgeType
from ..graph import CognitiveGraph


def constrained_traversal(
    graph: CognitiveGraph,
    start_node_id: str,
    allowed_edge_types: Iterable[EdgeType],
    max_depth: int = 3
) -> List[str]:
    """
    Traverses the graph only through specific edge types.
    """
    allowed_types = set(allowed_edge_types)
    result: List[str] = []
    visited: Set[str] = {start_node_id}
    stack = [(start_node_id, 0)]

    while stack:
        node_id, depth = stack.pop()
        result.append(node_id)
        
        if depth < max_depth:
            for edge in graph.get_outgoing_edges(node_id):
                if edge.edge_type in allowed_types and edge.target not in visited:
                    visited.add(edge.target)
                    stack.append((edge.target, depth + 1))

    return result
