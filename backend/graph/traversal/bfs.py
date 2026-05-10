"""
graph/traversal/bfs.py — Breadth-First Search traversal.
"""
from __future__ import annotations

from collections import deque
from typing import List, Set, Optional, Callable
from ..graph import CognitiveGraph
from ..node import Node


def bfs(
    graph: CognitiveGraph,
    start_node_id: str,
    max_depth: int = 3,
    visitor: Optional[Callable[[Node], None]] = None
) -> List[str]:
    """
    Standard BFS traversal.
    Returns a list of node IDs in the order they were visited.
    """
    visited: Set[str] = {start_node_id}
    queue = deque([(start_node_id, 0)])
    result: List[str] = []

    while queue:
        node_id, depth = queue.popleft()
        result.append(node_id)
        
        node = graph.get_node(node_id)
        if node and visitor:
            visitor(node)

        if depth < max_depth:
            for edge in graph.get_outgoing_edges(node_id):
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, depth + 1))

    return result
