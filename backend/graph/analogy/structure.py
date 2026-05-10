"""graph/analogy/structure.py — Structural motif matching for analogy detection."""
from __future__ import annotations

from typing import Dict, List, Set, Tuple
from graph.graph import GraphEngine


def get_structural_motif(graph: GraphEngine, label: str) -> Dict[str, int]:
    """
    Extracts the 'structural motif' of a node: a counts of its outgoing edge types.
    Example: {CAUSES: 2, IS_A: 1}
    """
    neighbors = graph.get_neighbors(label)
    motif: Dict[str, int] = {}
    for edge in neighbors:
        t = edge.type.value
        motif[t] = motif.get(t, 0) + 1
    return motif


def compare_motifs(m1: Dict[str, int], m2: Dict[str, int]) -> float:
    """
    Calculates cosine-like similarity between two structural motifs.
    """
    if not m1 or not m2:
        return 0.0
    
    all_types = set(m1.keys()) | set(m2.keys())
    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0
    
    for t in all_types:
        v1 = m1.get(t, 0)
        v2 = m2.get(t, 0)
        dot_product += v1 * v2
        norm_a += v1 * v1
        norm_b += v2 * v2
        
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))


import math
