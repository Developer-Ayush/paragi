"""graph/graph_store.py — The primary interface for graph data persistence."""
from __future__ import annotations

import threading
from typing import Dict, List, Optional
from .node import Node
from .edge import Edge
from .schemas import NodeSchema, EdgeSchema

class GraphStore:
    """
    In-memory graph store representing the core semantic topography.
    Provides fast O(1) access to Nodes and Edges.
    """
    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._adj_out: Dict[str, List[str]] = {}
        self._adj_in: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def add_node(self, node: Node) -> None:
        with self._lock:
            self._nodes[node.id] = node
            if node.id not in self._adj_out:
                self._adj_out[node.id] = []
                self._adj_in[node.id] = []

    def get_node(self, node_id: str) -> Optional[Node]:
        with self._lock:
            return self._nodes.get(node_id)

    def add_edge(self, edge: Edge) -> None:
        with self._lock:
            self._edges[edge.id] = edge
            if edge.source not in self._adj_out:
                self._adj_out[edge.source] = []
            if edge.target not in self._adj_in:
                self._adj_in[edge.target] = []
            
            if edge.id not in self._adj_out[edge.source]:
                self._adj_out[edge.source].append(edge.id)
            if edge.id not in self._adj_in[edge.target]:
                self._adj_in[edge.target].append(edge.id)

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        with self._lock:
            return self._edges.get(edge_id)

    def get_outgoing(self, node_id: str) -> List[Edge]:
        with self._lock:
            edge_ids = self._adj_out.get(node_id, [])
            return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_incoming(self, node_id: str) -> List[Edge]:
        with self._lock:
            edge_ids = self._adj_in.get(node_id, [])
            return [self._edges[eid] for eid in edge_ids if eid in self._edges]
