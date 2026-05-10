"""graph/analogy/graph_similarity.py — Isomorphism and structural similarity."""
from __future__ import annotations

def calculate_graph_similarity(graph_a: dict, graph_b: dict) -> float:
    """Calculates structural overlap between two subgraphs (not word embeddings)."""
    # Simple Jaccard over relation types
    edges_a = set(e.get("type") for e in graph_a.get("relations", []))
    edges_b = set(e.get("type") for e in graph_b.get("relations", []))
    
    if not edges_a and not edges_b:
        return 0.0
        
    intersection = len(edges_a.intersection(edges_b))
    union = len(edges_a.union(edges_b))
    
    return intersection / union if union > 0 else 0.0
