"""
graph/traversal/weighted.py — Weighted traversal based on synaptic strength.
"""
from __future__ import annotations

import heapq
from typing import List, Set, Dict, Optional
from ..graph import CognitiveGraph


def weighted_traversal(
    graph: CognitiveGraph,
    start_node_id: str,
    max_nodes: int = 10,
    min_weight: float = 0.05
) -> List[str]:
    """
    Traverses the graph prioritizing edges with higher weights.
    Similar to Dijkstra but for exploration rather than pathfinding.
    """
    # Priority queue: (-weight, node_id) -> max heap
    pq = [(-1.0, start_node_id)]
    visited: Set[str] = set()
    result: List[str] = []

    while pq and len(result) < max_nodes:
        neg_weight, node_id = heapq.heappop(pq)
        weight = -neg_weight
        
        if node_id in visited:
            continue
            
        visited.add(node_id)
        result.append(node_id)
        
        for edge in graph.get_outgoing_edges(node_id):
            if edge.target not in visited and edge.weight >= min_weight:
                # Cumulative weight or just local? Exploring usually uses cumulative
                # but for simplicity we'll use local weight * incoming weight
                heapq.heappush(pq, (-(weight * edge.weight), edge.target))

    return result
