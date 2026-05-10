"""graph/analogy/transfer.py — Apply analogy-based inference to suggest new edges."""
from __future__ import annotations
from typing import List, Tuple
from graph.graph import GraphEngine, AnalogyCandidate


def transfer_edges(
    graph: GraphEngine, source_label: str, analog_label: str,
    *, dry_run: bool = True,
) -> List[Tuple[str, str, str]]:
    """
    Transfer edges from analog_label to source_label where source doesn't have them.
    Returns list of (source, edge_type, target) tuples for proposed edges.
    If dry_run=False, actually creates the edges in the graph.
    """
    source_node = graph.get_node_by_label(source_label)
    analog_node = graph.get_node_by_label(analog_label)
    if source_node is None or analog_node is None:
        return []

    source_targets = {
        (e.type, graph.get_node_label(e.target))
        for e in graph.store.list_outgoing(source_node.id)
    }
    proposed: List[Tuple[str, str, str]] = []
    for edge in graph.store.list_outgoing(analog_node.id):
        target_label = graph.get_node_label(edge.target)
        key = (edge.type, target_label)
        if key not in source_targets:
            proposed.append((source_label, edge.type, target_label))
            if not dry_run:
                from core.enums import EdgeType
                try:
                    etype = EdgeType(edge.type)
                except ValueError:
                    etype = EdgeType.INFERRED
                graph.create_edge(source_label, target_label, etype, strength=0.2, confidence=0.4)
    return proposed
