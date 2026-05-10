"""
graph/activation/salience.py — Salience detection.

Calculates which nodes are most 'top-of-mind' based on current 
activation and structural importance.
"""
from __future__ import annotations

import time
from typing import List, Tuple
from ..graph import CognitiveGraph
from ..node import Node


def get_salient_nodes(
    graph: CognitiveGraph,
    limit: int = 10,
    decay_hours: float = 24.0
) -> List[Tuple[str, float]]:
    """
    Returns a list of (node_id, salience_score) for the most salient nodes.
    Salience combines current activation with temporal decay.
    """
    current_time = time.time()
    salience_scores: List[Tuple[str, float]] = []
    
    # Iterate through all nodes in the graph
    # In a real system, we'd only check nodes with activation > 0
    for node_id, node in graph._nodes.items():
        score = node.compute_salience(current_time, decay_hours)
        if score > 0:
            salience_scores.append((node_id, score))
            
    # Sort by score descending
    salience_scores.sort(key=lambda x: x[1], reverse=True)
    
    return salience_scores[:limit]
