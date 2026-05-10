"""graph/analogy/matcher.py — Structural analogy detection via Jaccard similarity."""
from __future__ import annotations
from typing import List
from graph.graph import GraphEngine, AnalogyCandidate


def find_analogies(
    graph: GraphEngine, source_label: str,
    *, limit: int = 10, min_shared: int = 2,
) -> List[AnalogyCandidate]:
    """Return structurally analogous concepts for source_label."""
    return graph.find_analogy_candidates(source_label, limit=limit, min_shared_neighbors=min_shared)
