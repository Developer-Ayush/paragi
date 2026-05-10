"""reasoning/analogy_reasoner.py — Structural analogy reasoning via relational motif matching."""
from __future__ import annotations

from typing import List, Dict, Any
from graph.graph import GraphEngine, AnalogyCandidate
from core.semantic_ir import SemanticIR
from graph.analogy.structure import get_structural_motif, compare_motifs
from .engine import ReasoningResult


def analogy_reason(graph: GraphEngine, ir: SemanticIR, concept: str) -> ReasoningResult:
    """
    Finds structural analogies for a concept.
    Uses relational motif matching to find nodes with similar 'roles' in the graph.
    """
    node = graph.get_node_by_label(concept)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="analogy", used_fallback=True)

    # 1. Get structural motif of source
    source_motif = get_structural_motif(graph, concept)
    
    # 2. Find candidates (initial filtering by neighbors, then motif comparison)
    # Using the legacy matcher for initial candidates
    initial_candidates = graph.find_analogy_candidates(concept, limit=20, min_shared_neighbors=1)
    
    scored_candidates: List[Dict[str, Any]] = []
    for cand in initial_candidates:
        target_motif = get_structural_motif(graph, cand.candidate_label)
        motif_similarity = compare_motifs(source_motif, target_motif)
        
        # Combined score: 60% Motif, 40% Jaccard
        final_score = (motif_similarity * 0.6) + (cand.jaccard * 0.4)
        
        scored_candidates.append({
            "label": cand.candidate_label,
            "motif_sim": motif_similarity,
            "jaccard": cand.jaccard,
            "score": final_score,
            "shared": cand.shared_neighbors
        })

    scored_candidates.sort(key=lambda x: -x["score"])
    
    if not scored_candidates or scored_candidates[0]["score"] < 0.2:
        return ReasoningResult(
            answer=f"No strong structural analogies found for '{concept}'.",
            confidence=0.0,
            mode="analogy"
        )

    # 3. Format top result
    top = scored_candidates[0]
    shared_str = ", ".join(top["shared"][:3])
    answer = (
        f"'{concept}' is structurally analogous to '{top['label']}'. "
        f"They share a {top['motif_sim']:.1%} similarity in relational patterns "
        f"and common associations like: {shared_str}."
    )
    
    return ReasoningResult(
        answer=answer,
        confidence=top["score"],
        node_path=[concept, top["label"]],
        mode="analogy",
        extra={"analogies": [c["label"] for c in scored_candidates[:3]]}
    )
