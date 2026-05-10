"""graph/activation/spread.py — Spreading activation from seed nodes."""
from __future__ import annotations
from typing import Dict, List
from graph.graph import GraphEngine


def spread_activation(
    graph: GraphEngine,
    seeds: List[str],
    *,
    decay: float = 0.5,
    max_depth: int = 3,
    threshold: float = 0.05,
) -> Dict[str, float]:
    """
    Spreading activation: starts at seed nodes and propagates activation
    outward through edges, decayed by edge strength and hop distance.

    Returns {node_label: activation_level}.
    """
    activation: Dict[str, float] = {}

    # Initialize seeds
    for seed in seeds:
        node = graph.get_node_by_label(seed)
        if node:
            activation[node.id] = 1.0

    # Spread layer by layer
    for depth in range(max_depth):
        next_activation: Dict[str, float] = dict(activation)
        for node_id, level in activation.items():
            if level < threshold:
                continue
            for edge in graph.store.list_outgoing(node_id):
                spread = level * edge.strength * (decay ** (depth + 1))
                if spread >= threshold:
                    existing = next_activation.get(edge.target, 0.0)
                    next_activation[edge.target] = max(existing, spread)
        activation = next_activation

    # Convert IDs to labels
    return {
        graph.get_node_label(nid): level
        for nid, level in activation.items()
        if level >= threshold
    }
