"""graph/traversal/semantic.py — Embedding-vector guided semantic traversal."""
from __future__ import annotations
import math
from typing import List
from graph.graph import GraphEngine


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_neighbors(
    graph: GraphEngine, label: str,
    query_vector: List[float],
    *, top_k: int = 5, min_similarity: float = 0.1,
) -> List[tuple]:
    """Return top-k neighbors ranked by edge vector similarity to query_vector."""
    neighbors = graph.get_neighbors(label)
    scored = []
    for edge in neighbors:
        if not edge.vector:
            continue
        sim = cosine_similarity(query_vector, edge.vector[:len(query_vector)])
        if sim >= min_similarity:
            target_label = graph.get_node_label(edge.target)
            scored.append((target_label, sim, edge))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
