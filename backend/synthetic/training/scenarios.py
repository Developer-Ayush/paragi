"""
synthetic/training/scenarios.py — Standard cognitive scenarios.
"""
from __future__ import annotations

from core.enums import EdgeType
from graph.node import Node
from graph.edge import Edge
from .generator import SyntheticGraphGenerator


def load_water_cycle(gen: SyntheticGraphGenerator):
    """Scenario: Causal chain of the water cycle."""
    gen.generate_chain([
        "Sun", "Heat", "Evaporation", "Clouds", "Condensation", "Rain", "River", "Ocean"
    ], EdgeType.CAUSES)


def load_atom_solar_analogy(gen: SyntheticGraphGenerator):
    """Scenario: Structural mapping between Atom and Solar System."""
    
    def add_node(label):
        nid = gen._get_id(label)
        if not gen.graph.get_node(nid):
            gen.graph.add_node(Node(id=nid, label=label))
        return nid

    def add_edge(s, t, et):
        sid = add_node(s)
        tid = add_node(t)
        gen.graph.add_edge(Edge(source=sid, target=tid, edge_type=et, weight=0.9))

    # Solar System Hub
    add_edge("Solar System", "Sun", EdgeType.ASSOCIATED_WITH)
    add_edge("Sun", "Gravity", EdgeType.CAUSES)
    add_edge("Sun", "Orbit", EdgeType.CAUSES)
    add_edge("Sun", "Planets", EdgeType.ASSOCIATED_WITH)
    
    # Atom Hub
    add_edge("Atom", "Nucleus", EdgeType.ASSOCIATED_WITH)
    add_edge("Nucleus", "Electromagnetism", EdgeType.CAUSES)
    add_edge("Nucleus", "Shell", EdgeType.CAUSES)
    add_edge("Nucleus", "Electrons", EdgeType.ASSOCIATED_WITH)
