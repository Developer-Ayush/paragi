"""reasoning/planning_reasoner.py — Recursive dependency resolution and goal planning."""
from __future__ import annotations

from typing import List, Set, Dict, Optional, Tuple
from graph.graph import GraphEngine, PathMatch
from core.semantic_ir import SemanticIR
from core.enums import EdgeType
from .engine import ReasoningResult


def planning_reason(graph: GraphEngine, ir: SemanticIR, goal: str, max_depth: int = 5) -> ReasoningResult:
    """
    Derives a multi-step plan by recursively traversing DEPENDS_ON and PRECONDITION edges.
    Uses backwards chaining from the goal to the 'root' requirements.
    """
    visited: Set[str] = set()
    steps: List[str] = []
    total_confidence: float = 1.0
    paths: List[PathMatch] = []

    def resolve_dependencies(current_node: str, depth: int) -> float:
        nonlocal total_confidence
        if current_node in visited or depth > max_depth:
            return 1.0
        
        visited.add(current_node)
        neighbors = graph.get_neighbors(current_node)
        
        # We look for what the current node DEPENDS_ON
        deps = [n for n in neighbors if n.type in (EdgeType.DEPENDS_ON, EdgeType.PRECONDITION, EdgeType.GOAL)]
        
        if not deps:
            # This is a leaf node (a requirement we don't know how to fulfill further)
            return 1.0

        path_confidence = 0.0
        for edge in deps:
            target_label = graph.get_node_label(edge.target)
            steps.append(target_label)
            
            # Recurse
            branch_confidence = edge.strength * resolve_dependencies(target_label, depth + 1)
            path_confidence = max(path_confidence, branch_confidence)
            
            # Record for visualization
            paths.append(PathMatch(
                node_ids=[edge.source, edge.target],
                node_labels=[current_node, target_label],
                edge_ids=[edge.id],
                total_strength=edge.strength,
                confidence=edge.strength
            ))
            
        return path_confidence

    final_confidence = resolve_dependencies(goal, 0)
    
    if not steps:
        return ReasoningResult(
            answer=f"I don't know how to achieve the goal: '{goal}'. No dependencies found in graph.",
            confidence=0.0,
            mode="planning"
        )

    # Reverse steps to show from root to goal
    unique_steps = []
    for s in reversed(steps):
        if s not in unique_steps and s != goal:
            unique_steps.append(s)

    plan_text = "To achieve " + goal + ", follow these steps: " + " -> ".join(unique_steps) + "."
    
    return ReasoningResult(
        answer=plan_text,
        confidence=final_confidence,
        node_path=[goal] + unique_steps,
        paths=paths,
        mode="planning"
    )
