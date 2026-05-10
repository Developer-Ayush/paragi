"""
graph/activation/spread.py — Spreading Activation algorithm.
"""
from __future__ import annotations

from typing import Dict, List, Set
from ..graph import CognitiveGraph


def spread_activation(
    graph: CognitiveGraph,
    source_node_id: str,
    initial_energy: float = 1.0,
    decay_factor: float = 0.5,
    min_energy: float = 0.0001,
    max_hops: int = 10
) -> Dict[str, float]:
    """
    Propagates activation energy through the graph.
    Returns a mapping of node IDs to the activation they received in this pass.
    """
    activation_delta: Dict[str, float] = {}
    
    def _spread(node_id: str, energy: float, depth: int):
        if energy < min_energy or depth > max_hops:
            return
            
        # Update delta
        activation_delta[node_id] = activation_delta.get(node_id, 0.0) + energy
        
        # Propagate to neighbors
        for edge in graph.get_outgoing_edges(node_id):
            # Energy transfer depends on edge weight and decay
            transfer = energy * edge.weight * decay_factor
            _spread(edge.target, transfer, depth + 1)

    _spread(source_node_id, initial_energy, 0)
    
    # Apply deltas to graph nodes
    for nid, delta in activation_delta.items():
        node = graph.get_node(nid)
        if node:
            node.set_activation(node.activation + delta)
            
    return activation_delta
