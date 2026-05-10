"""graph/traversal/weighted.py — Strength-weighted path scoring."""
from __future__ import annotations
from typing import List
from graph.graph import GraphEngine, PathMatch

def best_weighted_path(graph: GraphEngine, source: str, target: str, **kwargs) -> PathMatch | None:
    """Return the single highest-strength path between source and target."""
    paths = graph.find_paths(source, target, **kwargs)
    return paths[0] if paths else None

def top_weighted_paths(graph: GraphEngine, source: str, target: str, *, n: int = 5, **kwargs) -> List[PathMatch]:
    """Return top-n paths sorted by mean_strength."""
    paths = graph.find_paths(source, target, **kwargs)
    return sorted(paths, key=lambda p: -p.mean_strength)[:n]
