"""graph/traversal/dfs.py — DFS traversal (wraps GraphEngine.find_paths)."""
from __future__ import annotations
from typing import List, Optional
from graph.graph import GraphEngine, PathMatch

def dfs_paths(
    graph: GraphEngine, source: str, target: str,
    *, max_hops: int = 7, max_paths: int = 64,
    edge_type_filter: Optional[List[str]] = None,
) -> List[PathMatch]:
    return graph.find_paths(
        source, target, max_hops=max_hops, max_paths=max_paths,
        edge_type_filter=edge_type_filter,
    )
