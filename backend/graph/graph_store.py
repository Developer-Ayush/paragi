"""
graph/graph_store.py — The primary interface for graph data persistence.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Any


class GraphStore:
    """Interface for graph storage."""
    def list_nodes(self) -> List[Dict[str, Any]]: raise NotImplementedError
    def upsert_node(self, data: Dict[str, Any]) -> None: raise NotImplementedError
    def delete_node(self, node_id: str) -> None: raise NotImplementedError
    
    def list_edges(self) -> List[Dict[str, Any]]: raise NotImplementedError
    def upsert_edge(self, data: Dict[str, Any]) -> None: raise NotImplementedError
    def delete_edge(self, source: str, target: str) -> None: raise NotImplementedError
    def list_outgoing(self, source_id: str) -> List[Dict[str, Any]]: raise NotImplementedError
    
    def close(self) -> None: pass


class InMemoryGraphStore(GraphStore):
    """
    In-memory graph store representing the core semantic topography.
    """
    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def list_nodes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._nodes.values())

    def upsert_node(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self._nodes[data["id"]] = data

    def delete_node(self, node_id: str) -> None:
        with self._lock:
            self._nodes.pop(node_id, None)

    def list_edges(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._edges.values())

    def upsert_edge(self, data: Dict[str, Any]) -> None:
        with self._lock:
            key = f"{data['source']}->{data['target']}"
            self._edges[key] = data

    def delete_edge(self, source: str, target: str) -> None:
        with self._lock:
            key = f"{source}->{target}"
            self._edges.pop(key, None)

    def list_outgoing(self, source_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [e for e in self._edges.values() if e["source"] == source_id]
