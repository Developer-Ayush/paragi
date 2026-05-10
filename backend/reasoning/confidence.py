"""reasoning/confidence.py — Confidence computation for reasoning results."""
from __future__ import annotations
from typing import List
from graph.graph import PathMatch


def compute_path_confidence(paths: List[PathMatch]) -> float:
    """Compute overall confidence from a list of paths."""
    if not paths:
        return 0.0
    path_count = len(paths)
    top_strength = paths[0].mean_strength if paths else 0.0
    path_bonus = min(0.3, path_count * 0.05)
    return min(1.0, top_strength + path_bonus)


def consensus_confidence(path_count: int, *, cause_threshold: int = 3) -> float:
    if path_count == 0:
        return 0.0
    if path_count >= cause_threshold:
        return min(0.95, 0.6 + path_count * 0.05)
    return min(0.6, path_count * 0.2)


def blend_confidences(confidences: List[float], weights: List[float] | None = None) -> float:
    if not confidences:
        return 0.0
    if weights is None:
        weights = [1.0] * len(confidences)
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0
    return sum(c * w for c, w in zip(confidences, weights)) / total_weight
