"""graph/analogy/abstraction.py — Shared ancestor detection for abstraction reasoning."""
from __future__ import annotations
from typing import List, Set
from graph.graph import GraphEngine


def find_shared_ancestors(
    graph: GraphEngine, label_a: str, label_b: str,
    *, max_hops: int = 4,
) -> List[str]:
    """
    Find shared ancestors of two concepts via IS_A / ABSTRACTS_TO edges.
    Returns list of shared ancestor labels sorted by proximity.
    """
    def ancestors(label: str) -> Set[str]:
        found: Set[str] = set()
        node = graph.get_node_by_label(label)
        if node is None:
            return found
        visited = {node.id}
        queue = [node.id]
        depth = 0
        while queue and depth < max_hops:
            next_queue = []
            for nid in queue:
                for edge in graph.store.list_outgoing(nid):
                    if edge.type in ("IS_A", "ABSTRACTS_TO") and edge.target not in visited:
                        visited.add(edge.target)
                        found.add(graph.get_node_label(edge.target))
                        next_queue.append(edge.target)
            queue = next_queue
            depth += 1
        return found

    anc_a = ancestors(label_a)
    anc_b = ancestors(label_b)
    return sorted(anc_a & anc_b)
