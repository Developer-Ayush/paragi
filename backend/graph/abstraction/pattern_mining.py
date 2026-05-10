"""graph/abstraction/pattern_mining.py — Frequent subgraph pattern mining."""
from __future__ import annotations
from graph.graph_store import GraphStore
from collections import defaultdict

class PatternMiner:
    """
    Identifies recurring structural patterns in the cognitive graph.
    Used to form new abstractions automatically (unsupervised learning).
    """
    def __init__(self, store: GraphStore):
        self.store = store

    def mine_frequent_motifs(self) -> list[dict]:
        """Identify common subgraph shapes (e.g., nodes with many outgoing same-type edges)."""
        motifs = []
        # Basic heuristic: look for hub nodes acting as centers
        for node_id in self.store._nodes.keys():
            outgoing = self.store.get_outgoing(node_id)
            if len(outgoing) > 5:
                types = defaultdict(int)
                for e in outgoing:
                    types[e.type.value] += 1
                
                dominant_type = max(types.items(), key=lambda x: x[1], default=(None, 0))
                if dominant_type[1] >= 3:
                    motifs.append({
                        "hub_id": node_id,
                        "dominant_relation": dominant_type[0],
                        "count": dominant_type[1]
                    })
        return sorted(motifs, key=lambda x: x["count"], reverse=True)
