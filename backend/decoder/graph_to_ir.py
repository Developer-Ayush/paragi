"""decoder/graph_to_ir.py — Convert activated graph state to intermediate representation."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from graph.graph import GraphEngine


@dataclass
class GraphIR:
    """Intermediate representation of the activated graph state."""
    focal_nodes: List[str] = field(default_factory=list)
    active_edges: List[Dict[str, Any]] = field(default_factory=list)
    fact_triples: List[tuple] = field(default_factory=list)   # (src, edge_type, tgt)
    summary_nodes: List[str] = field(default_factory=list)
    confidence: float = 0.0


def graph_to_ir(
    graph: GraphEngine,
    activated_nodes: List[str],
    *,
    max_edges: int = 10,
) -> GraphIR:
    """Convert an activated subgraph into a GraphIR for the decoder."""
    gir = GraphIR()
    gir.focal_nodes = activated_nodes[:5]

    seen_triples = set()
    for label in activated_nodes[:8]:
        node = graph.get_node_by_label(label)
        if node is None:
            continue
        for edge in sorted(graph.store.list_outgoing(node.id), key=lambda e: -e.strength)[:3]:
            target_label = graph.get_node_label(edge.target)
            triple = (label, edge.type, target_label)
            if triple not in seen_triples:
                seen_triples.add(triple)
                gir.active_edges.append({
                    "source": label, "type": edge.type,
                    "target": target_label, "strength": edge.strength,
                })
                gir.fact_triples.append(triple)
            if len(gir.active_edges) >= max_edges:
                break

    gir.summary_nodes = list({t for _, _, t in gir.fact_triples} | set(activated_nodes[:3]))[:6]
    if gir.active_edges:
        gir.confidence = sum(e["strength"] for e in gir.active_edges) / len(gir.active_edges)
    return gir
