"""
memory/reinforcement.py — High-fidelity synaptic reinforcement.
"""
from __future__ import annotations

from typing import List, Optional
from graph.graph import CognitiveGraph


class SynapticReinforcer:
    """
    Manages the strengthening of synaptic connections (edges) based on usage.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def reinforce_path(self, node_ids: List[str], salience_context: float = 0.8) -> None:
        """
        Strengthens all edges along a reasoning path.
        """
        for i in range(len(node_ids) - 1):
            source = node_ids[i]
            target = node_ids[i+1]
            
            # Find all edges between these nodes
            edges = self.graph.get_edges_between(source, target)
            for edge in edges:
                # Apply high-fidelity Hebbian reinforcement
                edge.reinforce(s_score=salience_context)
                
                # Persistence update (if needed)
                self.graph._store.upsert_edge(edge.to_dict())
