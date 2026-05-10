"""graph/traversal/bfs.py — BFS traversal for breadth-first neighborhood expansion."""
from __future__ import annotations
from collections import deque
from typing import Dict, List, Optional, Set
from graph.graph import GraphEngine


def bfs_neighbors(
    graph: GraphEngine, start_label: str,
    *, max_depth: int = 3, edge_type_filter: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    BFS from start_label up to max_depth hops.
    Returns {node_label: depth} for all reachable nodes.
    """
    start = graph.get_node_by_label(start_label)
    if start is None:
        return {}

    visited: Dict[str, int] = {start.id: 0}
    queue: deque = deque([(start.id, 0)])

    while queue:
        current_id, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in graph.store.list_outgoing(current_id):
            if edge_type_filter and edge.type not in edge_type_filter:
                continue
            if edge.target not in visited:
                visited[edge.target] = depth + 1
                queue.append((edge.target, depth + 1))

    # Convert node IDs to labels
    return {graph.get_node_label(nid): d for nid, d in visited.items()}
