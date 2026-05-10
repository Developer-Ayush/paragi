"""graph/abstraction/pattern_mining.py — Discovery of recurring relational motifs."""
from __future__ import annotations

from typing import Dict, List, Tuple
from graph.graph import GraphEngine


def mine_frequent_patterns(graph: GraphEngine, min_count: int = 3) -> List[Tuple[str, str, int]]:
    """
    Identifies recurring relational structures in the graph.
    Returns a list of (EdgeType, target_label_substring, count).
    """
    patterns: Dict[Tuple[str, str], int] = {}
    
    for node_id in graph.store.iter_node_ids():
        edges = graph.store.list_outgoing(node_id)
        for edge in edges:
            target_label = graph.get_node_label(edge.target)
            # Find common suffixes or prefixes (categories)
            if " " in target_label:
                category = target_label.split()[-1]
                pattern = (edge.type.value, category)
                patterns[pattern] = patterns.get(pattern, 0) + 1
                
    # Filter by min_count and sort
    sorted_patterns = [
        (etype, cat, count) 
        for (etype, cat), count in patterns.items() 
        if count >= min_count
    ]
    sorted_patterns.sort(key=lambda x: -x[2])
    
    return sorted_patterns
