"""graph/traversal/constrained.py — Edge-type-constrained traversal."""
from __future__ import annotations
from typing import List
from core.enums import EdgeType
from graph.graph import GraphEngine, PathMatch
from .dfs import dfs_paths

def causal_paths(graph: GraphEngine, source: str, target: str, **kwargs) -> List[PathMatch]:
    return dfs_paths(graph, source, target, edge_type_filter=["CAUSES", "CORRELATES"], **kwargs)

def temporal_paths(graph: GraphEngine, source: str, target: str, **kwargs) -> List[PathMatch]:
    return dfs_paths(graph, source, target, edge_type_filter=["TEMPORAL", "SEQUENCE"], **kwargs)

def analogy_paths(graph: GraphEngine, source: str, target: str, **kwargs) -> List[PathMatch]:
    return dfs_paths(graph, source, target, edge_type_filter=["ANALOGY", "SIMILARITY"], **kwargs)

def abstraction_paths(graph: GraphEngine, source: str, target: str, **kwargs) -> List[PathMatch]:
    return dfs_paths(graph, source, target, edge_type_filter=["IS_A", "ABSTRACTS_TO", "PART_OF"], **kwargs)

def goal_paths(graph: GraphEngine, source: str, target: str, **kwargs) -> List[PathMatch]:
    return dfs_paths(graph, source, target, edge_type_filter=["GOAL", "DEPENDS_ON"], **kwargs)
