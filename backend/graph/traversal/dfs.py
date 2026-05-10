"""
graph/traversal/dfs.py — Depth-First Search traversal.
"""
from __future__ import annotations

from typing import List, Set, Optional, Callable
from ..graph import CognitiveGraph
from ..node import Node


def dfs(
    graph: CognitiveGraph,
    start_node_id: str,
    max_depth: int = 3,
    visitor: Optional[Callable[[Node], None]] = None
) -> List[str]:
    """
    Standard DFS traversal.
    Returns a list of node IDs in the order they were visited.
    """
    result: List[str] = []
    visited: Set[str] = set()

    def _dfs(node_id: str, depth: int):
        if depth > max_depth or node_id in visited:
            return
        
        visited.add(node_id)
        result.append(node_id)
        
        node = graph.get_node(node_id)
        if node and visitor:
            visitor(node)
            
        for edge in graph.get_outgoing_edges(node_id):
            _dfs(edge.target, depth + 1)

    _dfs(start_node_id, 0)
    return result
