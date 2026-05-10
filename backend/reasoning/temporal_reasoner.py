"""reasoning/temporal_reasoner.py — Temporal sequence reasoning and state transitions."""
from __future__ import annotations

from typing import List, Set, Dict, Optional
from graph.graph import GraphEngine, PathMatch
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from .engine import ReasoningResult


def temporal_reason(graph: GraphEngine, ir: SemanticIR, source: str, target: Optional[str] = None) -> ReasoningResult:
    """
    Constructs a temporal sequence or state transition chain.
    If target is provided, finds the sequence from source to target.
    If target is None, finds the 'future' timeline from source.
    """
    node = graph.get_node_by_label(source)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="temporal", used_fallback=True)

    # 1. Traverse TEMPORAL and SEQUENCE edges
    timeline: List[str] = [source]
    visited = {node.id}
    current_id = node.id
    
    paths: List[PathMatch] = []
    if target:
        # Targeted search
        paths = graph.find_paths(source, target, max_hops=7, edge_type_filter=[EdgeType.TEMPORAL, EdgeType.SEQUENCE])
    
    # 2. General timeline expansion (from source forward)
    for _ in range(5):
        next_candidates = []
        for edge in graph.store.list_outgoing(current_id):
            if edge.type in (EdgeType.TEMPORAL, EdgeType.SEQUENCE) and edge.target not in visited:
                next_candidates.append(edge)
        
        if not next_candidates:
            break
            
        # Select strongest transition
        next_edge = max(next_candidates, key=lambda e: e.strength)
        target_label = graph.get_node_label(next_edge.target)
        timeline.append(target_label)
        visited.add(next_edge.target)
        current_id = next_edge.target

    if len(timeline) <= 1 and not paths:
        return ReasoningResult(
            answer=f"I don't have temporal information about '{source}'.",
            confidence=0.0,
            mode="temporal"
        )

    # 3. Format answer
    if target and paths:
        best_path = paths[0]
        answer = f"The sequence from '{source}' to '{target}' is: " + " -> ".join(best_path.node_labels) + "."
        confidence = best_path.confidence
    else:
        answer = f"The temporal sequence starting from '{source}' is: " + " -> ".join(timeline) + "."
        confidence = 0.7

    return ReasoningResult(
        answer=answer,
        confidence=confidence,
        node_path=timeline if not paths else paths[0].node_labels,
        paths=paths,
        mode="temporal",
        extra={"timeline_length": len(timeline)}
    )
