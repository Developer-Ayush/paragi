"""
graph/traversal/semantic.py — Traversal based on semantic activation.
"""
from __future__ import annotations

import heapq
from typing import List, Set, Optional
from ..graph import CognitiveGraph


def semantic_traversal(
    graph: CognitiveGraph,
    start_node_id: str,
    min_activation: float = 0.1,
    max_nodes: int = 20
) -> List[str]:
    """
    Traverses the graph based on node activation levels.
    """
    # Use max-heap for activation
    pq = []
    
    start_node = graph.get_node(start_node_id)
    if start_node:
        heapq.heappush(pq, (-start_node.activation, start_node_id))
    
    visited: Set[str] = set()
    result: List[str] = []

    while pq and len(result) < max_nodes:
        neg_act, node_id = heapq.heappop(pq)
        act = -neg_act
        
        if node_id in visited or act < min_activation:
            continue
            
        visited.add(node_id)
        result.append(node_id)
        
        for edge in graph.get_outgoing_edges(node_id):
            target_node = graph.get_node(edge.target)
            if target_node and target_node.id not in visited:
                # We consider the activation of the target node
                heapq.heappush(pq, (-target_node.activation, target_node.id))

    return result
