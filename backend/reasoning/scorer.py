"""reasoning/scorer.py — Score and rank reasoning results."""
from __future__ import annotations
from typing import List
from graph.graph import PathMatch


def score_paths(paths: List[PathMatch]) -> List[PathMatch]:
    """Sort paths by composite score (mean_strength, hops, goal_relevance)."""
    return sorted(paths, key=lambda p: (-p.score, p.hops, -p.mean_strength))


def top_paths(paths: List[PathMatch], *, n: int = 5) -> List[PathMatch]:
    return score_paths(paths)[:n]


def path_labels_to_str(path: PathMatch) -> str:
    return " -> ".join(path.node_labels)


def summarize_paths(paths: List[PathMatch], *, max_paths: int = 3) -> str:
    if not paths:
        return ""
    lines = []
    for i, p in enumerate(paths[:max_paths]):
        lines.append(f"Path {i+1}: {path_labels_to_str(p)} (strength={p.mean_strength:.2f}, hops={p.hops})")
    return "\n".join(lines)
