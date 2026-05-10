"""graph/activation/relevance.py — Query-relevance scoring for activated nodes."""
from __future__ import annotations
from typing import Dict, List
from graph.traversal.semantic import cosine_similarity


def score_by_relevance(
    activation_map: Dict[str, float],
    query_vector: List[float],
    graph: object,
    *,
    semantic_weight: float = 0.4,
    activation_weight: float = 0.6,
) -> Dict[str, float]:
    """
    Combine spreading activation scores with semantic similarity.
    Returns {node_label: combined_score}.
    """
    scored: Dict[str, float] = {}
    for label, act_level in activation_map.items():
        node = graph.get_node_by_label(label)  # type: ignore
        if node is None:
            scored[label] = act_level * activation_weight
            continue
        # Use node's edges' vectors for semantic similarity estimate
        edges = graph.store.list_outgoing(node.id)  # type: ignore
        if edges and query_vector:
            avg_sim = sum(
                cosine_similarity(query_vector, e.vector[:len(query_vector)])
                for e in edges if e.vector
            ) / len(edges)
        else:
            avg_sim = 0.0
        scored[label] = (activation_weight * act_level) + (semantic_weight * avg_sim)
    return scored


def top_relevant_nodes(scores: Dict[str, float], *, n: int = 10) -> List[str]:
    return sorted(scores, key=lambda k: -scores[k])[:n]
