"""reasoning/probabilistic_reasoner.py — Bayesian-style belief propagation across graph paths."""
from __future__ import annotations

import math
from typing import List, Optional
from graph.graph import GraphEngine, PathMatch
from core.semantic_ir import SemanticIR
from .engine import ReasoningResult


def probabilistic_reason(graph: GraphEngine, ir: SemanticIR, source: str, target: str) -> ReasoningResult:
    """
    Computes reasoning result using a Noisy-OR aggregate of all paths between source and target.
    
    In Noisy-OR, the probability that target is NOT activated by source is the product 
    of (1 - P(path_i)) for all paths.
    P(source -> target) = 1 - Π(1 - P(path_i))
    """
    paths: List[PathMatch] = graph.find_paths(source, target, max_hops=5, max_paths=20)
    if not paths:
        return ReasoningResult(
            answer=f"No probabilistic connection found between '{source}' and '{target}'.",
            confidence=0.0,
            mode="probabilistic"
        )

    # 1. Calculate path probabilities (product of edge strengths)
    path_probabilities: List[float] = []
    valid_paths: List[PathMatch] = []
    
    for path in paths:
        # Path probability is the product of all edge strengths in the chain
        p_path = 1.0
        for eid in path.edge_ids:
            edge = graph.get_edge_by_id(eid)
            if edge:
                p_path *= edge.strength
            else:
                p_path = 0.0
                break
        
        if p_path > 0.01:
            path.confidence = p_path
            path_probabilities.append(p_path)
            valid_paths.append(path)

    if not path_probabilities:
         return ReasoningResult(
            answer=f"The connection between '{source}' and '{target}' is too weak to measure.",
            confidence=0.0,
            mode="probabilistic"
        )

    # 2. Noisy-OR aggregation: P = 1 - product(1 - p_i)
    complement_product = 1.0
    for p in path_probabilities:
        complement_product *= (1.0 - p)
    
    aggregate_probability = 1.0 - complement_product
    
    # 3. Format answer
    path_count = len(valid_paths)
    answer = (
        f"Structural analysis reveals a {aggregate_probability:.2%} probability of connection "
        f"between '{source}' and '{target}', supported by {path_count} independent causal/associative chains."
    )
    
    valid_paths.sort(key=lambda p: -p.confidence)
    
    return ReasoningResult(
        answer=answer,
        confidence=aggregate_probability,
        paths=valid_paths[:5],  # Return top 5 paths for inspection
        node_path=valid_paths[0].node_labels if valid_paths else [source, target],
        mode="probabilistic"
    )
