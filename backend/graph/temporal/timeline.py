"""graph/temporal/timeline.py — Timeline construction from TEMPORAL edges."""
from __future__ import annotations
from typing import List, Tuple
from graph.graph import GraphEngine


def build_timeline(graph: GraphEngine, root_label: str, *, max_depth: int = 8) -> List[str]:
    """
    Follow TEMPORAL / SEQUENCE edges from root_label to build an ordered timeline.
    Returns a list of labels in temporal order.
    """
    timeline: List[str] = [root_label]
    visited = {root_label}
    current = root_label
    for _ in range(max_depth):
        node = graph.get_node_by_label(current)
        if node is None:
            break
        next_labels = [
            graph.get_node_label(e.target)
            for e in graph.store.list_outgoing(node.id)
            if e.type in ("TEMPORAL", "SEQUENCE")
        ]
        # Pick the strongest outgoing temporal edge
        next_candidates = sorted(
            [
                (graph.get_node_label(e.target), e.strength)
                for e in graph.store.list_outgoing(node.id)
                if e.type in ("TEMPORAL", "SEQUENCE") and graph.get_node_label(e.target) not in visited
            ],
            key=lambda x: -x[1],
        )
        if not next_candidates:
            break
        next_label = next_candidates[0][0]
        timeline.append(next_label)
        visited.add(next_label)
        current = next_label
    return timeline
