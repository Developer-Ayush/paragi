"""reasoning/predictive_reasoner.py — Probabilistic future projection and causal cascade analysis."""
from __future__ import annotations

import math
from typing import List, Dict, Tuple, Set
from graph.graph import GraphEngine, PathMatch
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from .engine import ReasoningResult


def predictive_reason(graph: GraphEngine, ir: SemanticIR, source: str) -> ReasoningResult:
    """
    Projects the future consequences of an event or concept.
    Explores multiple causal branches and aggregates probabilities of outcomes.
    """
    node = graph.get_node_by_label(source)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="predictive", used_fallback=True)

    # 1. Forward traversal through CAUSES and LEADS_TO
    # We use a breadth-first approach to aggregate probabilities at each 'step' in time
    outcomes: Dict[str, float] = {node.id: 1.0}
    visited: Set[str] = set()
    
    # Projection horizon (steps into future)
    for _ in range(3):
        new_outcomes: Dict[str, float] = {}
        for nid, prob in outcomes.items():
            if nid in visited: continue
            visited.add(nid)
            
            edges = [e for e in graph.store.list_outgoing(nid) 
                     if e.type in (EdgeType.CAUSES, EdgeType.CORRELATES) and e.target not in visited]
            
            for edge in edges:
                # Joint probability P(target) = P(source) * P(edge)
                p_next = prob * edge.strength
                new_outcomes[edge.target] = max(new_outcomes.get(edge.target, 0.0), p_next)
        
        # Merge new outcomes into main set
        for nid, p in new_outcomes.items():
            outcomes[nid] = max(outcomes.get(nid, 0.0), p)

    # 2. Filter and rank results
    # Remove the source itself and low-probability noise
    results = [
        (graph.get_node_label(nid), p) 
        for nid, p in outcomes.items() 
        if nid != node.id and p > 0.15
    ]
    results.sort(key=lambda x: -x[1])

    if not results:
        return ReasoningResult(
            answer=f"No clear future consequences found for '{source}'.",
            confidence=0.0,
            mode="predictive"
        )

    # 3. Format answer
    top_outcomes = [f"'{label}' ({p:.0%})" for label, p in results[:3]]
    answer = f"If '{source}' occurs, the most likely consequences are: " + ", ".join(top_outcomes) + "."
    
    return ReasoningResult(
        answer=answer,
        confidence=results[0][1],
        node_path=[source] + [r[0] for r in results[:3]],
        mode="predictive",
        extra={"all_outcomes": {r[0]: r[1] for r in results}}
    )
