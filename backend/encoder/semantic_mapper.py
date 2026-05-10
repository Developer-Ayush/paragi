"""encoder/semantic_mapper.py — Map extracted entities to graph-space concepts."""
from __future__ import annotations

from typing import List, Optional

from core.types import make_node_id
from .concept_normalizer import normalize_concept


def map_to_graph_concepts(entities: List[str]) -> List[str]:
    """
    Normalize and map extracted entities to canonical graph node labels.
    Returns deduplicated list of graph-ready concept strings.
    """
    seen = set()
    result = []
    for entity in entities:
        concept = normalize_concept(entity)
        if concept and concept not in seen:
            seen.add(concept)
            result.append(concept)
    return result


def concept_to_node_id(concept: str) -> str:
    """Convert a concept string to its deterministic graph node ID."""
    return make_node_id(normalize_concept(concept))


def find_graph_match(concept: str, existing_labels: List[str]) -> Optional[str]:
    """
    Find the closest existing graph label for a concept.
    Returns the matching label or None if no close match found.
    """
    normalized = normalize_concept(concept)
    # Exact match
    if normalized in existing_labels:
        return normalized
    # Prefix match (e.g., "fire" matches "fire truck")
    for label in existing_labels:
        if label.startswith(normalized) or normalized.startswith(label):
            return label
    return None
