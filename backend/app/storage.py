from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Iterable, List, Set

from .models import EdgeRecord, EdgeType, NodeRecord

try:
    import h5py  # type: ignore
    import numpy as np
except Exception:  # pragma: no cover - optional dependency in dev setups
    h5py = None
    np = None


class GraphStore(ABC):
    @abstractmethod
    def upsert_node(self, node: NodeRecord) -> NodeRecord:
        raise NotImplementedError

    @abstractmethod
    def get_node(self, node_id: str) -> NodeRecord | None:
        raise NotImplementedError

    @abstractmethod
    def iter_node_ids(self) -> Iterable[str]:
        raise NotImplementedError

    @abstractmethod
    def upsert_edge(self, edge: EdgeRecord) -> EdgeRecord:
        raise NotImplementedError

    @abstractmethod
    def get_edge(self, edge_id: str) -> EdgeRecord | None:
        raise NotImplementedError

    @abstractmethod
    def list_outgoing(self, source_id: str) -> List[EdgeRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_edge_ids(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def update_edge_strength(self, edge_id: str, new_strength: float, *, increment_recall: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_node(self, node_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_edge(self, edge_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_incoming(self, target_id: str) -> List[EdgeRecord]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class InMemoryGraphStore(GraphStore):
    def __init__(self) -> None:
        self.nodes: Dict[str, NodeRecord] = {}
        self.edges: Dict[str, EdgeRecord] = {}
        self.adj: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def upsert_node(self, node: NodeRecord) -> NodeRecord:
        with self._lock:
            existing = self.nodes.get(node.id)
            if existing is None:
                self.nodes[node.id] = node
                return node
            existing.last_accessed = node.last_accessed
            existing.access_count = node.access_count
            return existing

    def get_node(self, node_id: str) -> NodeRecord | None:
        with self._lock:
            return self.nodes.get(node_id)

    def iter_node_ids(self) -> Iterable[str]:
        with self._lock:
            return list(self.nodes.keys())

    def upsert_edge(self, edge: EdgeRecord) -> EdgeRecord:
        with self._lock:
            self.edges[edge.id] = edge
            self.adj.setdefault(edge.source, set()).add(edge.id)
            return edge

    def get_edge(self, edge_id: str) -> EdgeRecord | None:
        with self._lock:
            return self.edges.get(edge_id)

    def list_outgoing(self, source_id: str) -> List[EdgeRecord]:
        with self._lock:
            edge_ids = self.adj.get(source_id, set())
            return [self.edges[eid] for eid in edge_ids if eid in self.edges]

    def list_edge_ids(self) -> List[str]:
        with self._lock:
            return list(self.edges.keys())

    def update_edge_strength(self, edge_id: str, new_strength: float, *, increment_recall: bool) -> None:
        with self._lock:
            edge = self.edges.get(edge_id)
            if edge is None:
                return
            edge.strength = float(new_strength)
            if increment_recall:
                edge.recall_count += 1

    def delete_node(self, node_id: str) -> None:
        with self._lock:
            self.nodes.pop(node_id, None)
            self.adj.pop(node_id, None)

    def delete_edge(self, edge_id: str) -> None:
        with self._lock:
            edge = self.edges.pop(edge_id, None)
            if edge and edge.source in self.adj:
                self.adj[edge.source].discard(edge_id)

    def list_incoming(self, target_id: str) -> List[EdgeRecord]:
        with self._lock:
            return [e for e in self.edges.values() if e.target == target_id]

    def close(self) -> None:
        return


class HDF5GraphStore(GraphStore):
    def __init__(self, path: Path) -> None:
        if h5py is None or np is None:
            raise RuntimeError("HDF5GraphStore requires h5py and numpy. Install requirements first.")
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        # Windows + reload workflows can cause transient lock conflicts.
        # Best-effort locking keeps disk persistence while avoiding hard crashes.
        try:
            self._h5 = h5py.File(self.path, "a", locking="best-effort")
        except TypeError:
            self._h5 = h5py.File(self.path, "a")
        self._nodes = self._h5.require_group("nodes")
        self._edges = self._h5.require_group("edges")
        self._adj = self._h5.require_group("adjacency")

    def _edge_from_group(self, group) -> EdgeRecord:
        vector = group["vector"][()].astype("float32").tolist()
        return EdgeRecord(
            id=str(group.attrs["id"]),
            source=str(group.attrs["source"]),
            target=str(group.attrs["target"]),
            type=EdgeType(str(group.attrs["type"])),
            vector=vector,
            strength=float(group.attrs["strength"]),
            emotional_weight=float(group.attrs["emotional_weight"]),
            recall_count=int(group.attrs["recall_count"]),
            stability=float(group.attrs["stability"]),
            last_activated=float(group.attrs["last_activated"]),
            created=float(group.attrs["created"]),
        )

    def _node_from_group(self, group) -> NodeRecord:
        return NodeRecord(
            id=str(group.attrs["id"]),
            label=str(group.attrs["label"]),
            created=float(group.attrs["created"]),
            last_accessed=float(group.attrs["last_accessed"]),
            access_count=int(group.attrs["access_count"]),
        )

    def upsert_node(self, node: NodeRecord) -> NodeRecord:
        with self._lock:
            if node.id in self._nodes:
                grp = self._nodes[node.id]
                grp.attrs["last_accessed"] = float(node.last_accessed)
                grp.attrs["access_count"] = int(node.access_count)
                return self._node_from_group(grp)

            grp = self._nodes.create_group(node.id)
            grp.attrs["id"] = node.id
            grp.attrs["label"] = node.label
            grp.attrs["created"] = float(node.created)
            grp.attrs["last_accessed"] = float(node.last_accessed)
            grp.attrs["access_count"] = int(node.access_count)
            self._h5.flush()
            return node

    def get_node(self, node_id: str) -> NodeRecord | None:
        with self._lock:
            if node_id not in self._nodes:
                return None
            return self._node_from_group(self._nodes[node_id])

    def iter_node_ids(self) -> Iterable[str]:
        with self._lock:
            return list(self._nodes.keys())

    def upsert_edge(self, edge: EdgeRecord) -> EdgeRecord:
        with self._lock:
            if edge.id in self._edges:
                grp = self._edges[edge.id]
                grp.attrs["type"] = edge.type.value
                grp.attrs["strength"] = float(edge.strength)
                grp.attrs["emotional_weight"] = float(edge.emotional_weight)
                grp.attrs["recall_count"] = int(edge.recall_count)
                grp.attrs["stability"] = float(edge.stability)
                grp.attrs["last_activated"] = float(edge.last_activated)
                grp["vector"][()] = np.array(edge.vector, dtype=np.float32)
            else:
                grp = self._edges.create_group(edge.id)
                grp.attrs["id"] = edge.id
                grp.attrs["source"] = edge.source
                grp.attrs["target"] = edge.target
                grp.attrs["type"] = edge.type.value
                grp.attrs["strength"] = float(edge.strength)
                grp.attrs["emotional_weight"] = float(edge.emotional_weight)
                grp.attrs["recall_count"] = int(edge.recall_count)
                grp.attrs["stability"] = float(edge.stability)
                grp.attrs["last_activated"] = float(edge.last_activated)
                grp.attrs["created"] = float(edge.created)
                grp.create_dataset("vector", data=np.array(edge.vector, dtype=np.float32))

            source_group = self._adj.require_group(edge.source)
            source_group.require_group(edge.id)
            self._h5.flush()
            return edge

    def get_edge(self, edge_id: str) -> EdgeRecord | None:
        with self._lock:
            if edge_id not in self._edges:
                return None
            return self._edge_from_group(self._edges[edge_id])

    def list_outgoing(self, source_id: str) -> List[EdgeRecord]:
        with self._lock:
            if source_id not in self._adj:
                return []
            edge_ids = list(self._adj[source_id].keys())
            result: List[EdgeRecord] = []
            for edge_id in edge_ids:
                if edge_id in self._edges:
                    result.append(self._edge_from_group(self._edges[edge_id]))
            return result

    def list_edge_ids(self) -> List[str]:
        with self._lock:
            return list(self._edges.keys())

    def update_edge_strength(self, edge_id: str, new_strength: float, *, increment_recall: bool) -> None:
        with self._lock:
            if edge_id not in self._edges:
                return
            grp = self._edges[edge_id]
            grp.attrs["strength"] = float(new_strength)
            if increment_recall:
                grp.attrs["recall_count"] = int(grp.attrs["recall_count"]) + 1
            self._h5.flush()

    def delete_node(self, node_id: str) -> None:
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
            if node_id in self._adj:
                del self._adj[node_id]
            self._h5.flush()

    def delete_edge(self, edge_id: str) -> None:
        with self._lock:
            if edge_id in self._edges:
                edge = self._edge_from_group(self._edges[edge_id])
                del self._edges[edge_id]
                if edge.source in self._adj and edge_id in self._adj[edge.source]:
                    del self._adj[edge.source][edge_id]
            self._h5.flush()

    def list_incoming(self, target_id: str) -> List[EdgeRecord]:
        with self._lock:
            result: List[EdgeRecord] = []
            for edge_id in self._edges.keys():
                grp = self._edges[edge_id]
                if str(grp.attrs["target"]) == target_id:
                    result.append(self._edge_from_group(grp))
            return result

    def close(self) -> None:
        with self._lock:
            self._h5.flush()
            self._h5.close()
