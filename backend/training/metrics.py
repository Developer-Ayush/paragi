"""training/metrics.py — Cognitive scoring functions."""
from __future__ import annotations

from typing import Dict, Any, List


def jaccard_similarity(set1: set, set2: set) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union


def score_semantic_ir(actual: Dict[str, Any], expected: Dict[str, Any]) -> float:
    """Calculates similarity between two SemanticIR dictionaries."""
    # 1. Intent match (binary)
    intent_score = 1.0 if actual.get("intent") == expected.get("intent") else 0.0
    
    # 2. Entity match (Jaccard)
    act_ent = set(actual.get("entities", []))
    exp_ent = set(expected.get("entities", []))
    entity_score = jaccard_similarity(act_ent, exp_ent)
    
    # 3. Relation match
    act_rel = {f"{r['source']}_{r['relation']}_{r['target']}" for r in actual.get("relations", [])}
    exp_rel = {f"{r['source']}_{r['relation']}_{r['target']}" for r in expected.get("relations", [])}
    relation_score = jaccard_similarity(act_rel, exp_rel)
    
    # Weighted composite
    return (intent_score * 0.2) + (entity_score * 0.3) + (relation_score * 0.5)


def path_validity_score(paths: List[Any]) -> float:
    """Scores a set of reasoning paths based on edge strength and coherence."""
    if not paths:
        return 0.0
    
    # Mean confidence across top 3 paths
    top_paths = sorted(paths, key=lambda p: -p.confidence)[:3]
    return sum(p.confidence for p in top_paths) / len(top_paths)
