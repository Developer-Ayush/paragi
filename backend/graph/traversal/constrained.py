from typing import List, Tuple, Set
from core.enums import EdgeType

def constrained_traversal(
    graph,
    start_node_id: str,
    allowed_edge_types: List[EdgeType],
    max_depth: int = 5
) -> List[Tuple[str, EdgeType, str]]:
    """
    Performs a breadth-first traversal starting from start_node_id,
    only following the allowed_edge_types.
    Returns a list of (source_id, edge_type, target_id) triples.
    """
    results = []
    visited = {start_node_id}
    queue = [(start_node_id, 0)]

    while queue:
        current_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        outgoing_edges = graph.get_outgoing_edges(current_id)
        for edge in outgoing_edges:
            if edge.edge_type in allowed_edge_types:
                results.append((edge.source, edge.edge_type, edge.target))
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, depth + 1))

    return results
