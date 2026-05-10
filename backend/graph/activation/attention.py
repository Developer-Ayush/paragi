"""graph/activation/attention.py — Attention-weighted node scoring."""
from __future__ import annotations
from typing import Dict, List
from graph.graph import GraphEngine


def attention_score(
    graph: GraphEngine,
    node_labels: List[str],
    query_tokens: List[str],
) -> Dict[str, float]:
    """
    Compute attention-weighted scores for nodes.
    Nodes whose labels share tokens with the query get higher attention.
    Combined with access_count for salience.
    """
    query_token_set = set(query_tokens)
    scores: Dict[str, float] = {}
    for label in node_labels:
        node = graph.get_node_by_label(label)
        if node is None:
            scores[label] = 0.0
            continue
        label_tokens = set(label.split())
        overlap = len(label_tokens & query_token_set)
        token_score = overlap / max(len(label_tokens), 1)
        access_score = min(node.access_count / 100.0, 1.0)
        scores[label] = 0.6 * token_score + 0.4 * access_score
    return scores
