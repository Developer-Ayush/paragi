"""
graph/persistence/hdf5_store.py — HDF5-backed graph persistence.
"""
from __future__ import annotations

import json
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

import h5py
import numpy as np

from graph.graph_store import GraphStore


class HDF5GraphStore(GraphStore):
    """
    HDF5 implementation of the GraphStore.
    Nodes and edges are stored in HDF5 groups.
    """
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._db: Optional[h5py.File] = None
        self._init_db()

    def _init_db(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = h5py.File(str(self.path), "a")
        if "nodes" not in self._db:
            self._db.create_group("nodes")
        if "edges" not in self._db:
            self._db.create_group("edges")

    def list_nodes(self) -> List[Dict[str, Any]]:
        with self._lock:
            nodes = []
            for node_id in self._db["nodes"]:
                node_data = self._db["nodes"][node_id].attrs.get("data")
                if node_data:
                    nodes.append(json.loads(node_data))
            return nodes

    def upsert_node(self, data: Dict[str, Any]) -> None:
        with self._lock:
            node_id = data["id"]
            if node_id in self._db["nodes"]:
                del self._db["nodes"][node_id]

            group = self._db["nodes"].create_group(node_id)
            group.attrs["data"] = json.dumps(data)

    def delete_node(self, node_id: str) -> None:
        with self._lock:
            if node_id in self._db["nodes"]:
                del self._db["nodes"][node_id]

    def list_edges(self) -> List[Dict[str, Any]]:
        with self._lock:
            edges = []
            for edge_id in self._db["edges"]:
                edge_data = self._db["edges"][edge_id].attrs.get("data")
                if edge_data:
                    edges.append(json.loads(edge_data))
            return edges

    def upsert_edge(self, data: Dict[str, Any]) -> None:
        with self._lock:
            edge_id = f"{data['source']}->{data['target']}"
            if edge_id in self._db["edges"]:
                del self._db["edges"][edge_id]

            group = self._db["edges"].create_group(edge_id)
            group.attrs["data"] = json.dumps(data)
            # Store the vector as a dataset for efficient access if needed
            if "vector" in data and data["vector"]:
                group.create_dataset("vector", data=np.array(data["vector"], dtype=np.float32))

    def delete_edge(self, source: str, target: str) -> None:
        with self._lock:
            edge_id = f"{source}->{target}"
            if edge_id in self._db["edges"]:
                del self._db["edges"][edge_id]

    def close(self) -> None:
        with self._lock:
            if self._db:
                self._db.close()
                self._db = None
