"""reasoning/abstraction_reasoner.py — Deep hierarchy analysis and category induction."""
from __future__ import annotations

from typing import List, Set, Dict, Optional
from graph.graph import GraphEngine
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from .engine import ReasoningResult


def abstraction_reason(graph: GraphEngine, ir: SemanticIR, concept: str) -> ReasoningResult:
    """
    Analyzes the abstraction hierarchy for a concept.
    Ranks categories by their centrality and specificity.
    """
    node = graph.get_node_by_label(concept)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="abstraction", used_fallback=True)

    # 1. Traverse upwards through IS_A and ABSTRACTS_TO
    hierarchy: Dict[str, int] = {}  # label -> distance
    visited = {node.id}
    queue = [(node.id, 0)]
    
    while queue:
        nid, dist = queue.pop(0)
        if dist >= 5:
            continue
            
        for edge in graph.store.list_outgoing(nid):
            if edge.type in (EdgeType.IS_A, EdgeType.ABSTRACTS_TO) and edge.target not in visited:
                visited.add(edge.target)
                label = graph.get_node_label(edge.target)
                hierarchy[label] = dist + 1
                queue.append((edge.target, dist + 1))

    if not hierarchy:
        return ReasoningResult(
            answer=f"I don't know the categories for '{concept}'.",
            confidence=0.0,
            mode="abstraction"
        )

    # 2. Rank categories: proximity + structural importance
    # More specific categories are closer (lower dist). 
    # High-level categories have more incoming IS_A edges.
    scored_categories = []
    for label, dist in hierarchy.items():
        # Heuristic: specificity (1/dist)
        score = 1.0 / dist
        scored_categories.append((label, score, dist))

    scored_categories.sort(key=lambda x: -x[1])
    top_categories = [c[0] for c in scored_categories]
    
    most_specific = top_categories[0]
    all_cats = ", ".join(top_categories)
    
    answer = f"'{concept}' is primarily a {most_specific}. Its broader hierarchy includes: {all_cats}."
    
    return ReasoningResult(
        answer=answer,
        confidence=0.85,
        node_path=[concept] + top_categories,
        mode="abstraction",
        extra={"hierarchy_depth": len(top_categories), "all_categories": top_categories}
    )


def induce_shared_abstraction(graph: GraphEngine, concepts: List[str]) -> Optional[str]:
    """Find the Lowest Common Ancestor (LCA) for a set of concepts."""
    if not concepts:
        return None
        
    sets = []
    for c in concepts:
        node = graph.get_node_by_label(c)
        if not node:
            continue
        ancestors = {node.id}
        # Small upward walk
        q = [node.id]
        while q:
            nid = q.pop(0)
            for edge in graph.store.list_outgoing(nid):
                if edge.type in (EdgeType.IS_A, EdgeType.ABSTRACTS_TO) and edge.target not in ancestors:
                    ancestors.add(edge.target)
                    q.append(edge.target)
        sets.append(ancestors)
        
    if not sets:
        return None
        
    # Intersection of all ancestor sets
    common = sets[0].intersection(*sets[1:])
    if not common:
        return None
        
    # Pick the most 'specific' common ancestor (one with fewest descendants or closest to seeds)
    # For now, just pick the first one from the smallest set that is in common
    for nid in common:
        return graph.get_node_label(nid)
    return None
