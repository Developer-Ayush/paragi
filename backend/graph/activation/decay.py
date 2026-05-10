"""
activation/decay.py — Global temporal decay.
"""
from __future__ import annotations

from graph.graph import CognitiveGraph
from core.constants import EDGE_DECAY_PER_CYCLE
from .vector_decay import apply_vector_decay


def apply_global_decay(graph: CognitiveGraph, rate: float = EDGE_DECAY_PER_CYCLE) -> None:
    """
    Applies temporal decay to all nodes and edges in the graph.
    """
    # 1. Decay Node Activation
    for node in graph._nodes.values():
        node.activation *= (1.0 - rate)
        if node.activation < 0.001:
            node.activation = 0.0
            
    # 2. Decay Edge Weights and Vectors
    for edge in graph._edges.values():
        # Scalar weight decay
        edge.weight *= (1.0 - rate)
        
        # High-fidelity vector decay
        edge.vector = apply_vector_decay(edge.vector, rate)
        
        # Persistence update
        graph.store.upsert_edge(edge.to_dict())
