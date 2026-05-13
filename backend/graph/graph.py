"""
graph/graph.py — CognitiveGraph: The orchestrator of the Paragi mind.

Manages the lifecycle of nodes and edges, handles activation propagation,
and provides high-level graph query and mutation interfaces.
"""
from __future__ import annotations

import math
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Iterable
from core.enums import EdgeType, NodeType
from core.logger import get_logger
from .node import Node
from .edge import Edge
from .graph_store import GraphStore

log = get_logger(__name__)


@dataclass
class PathMatch:
    """Represents a discovered path in the graph."""
    node_ids: List[str]
    node_labels: List[str]
    edge_ids: List[str]
    total_strength: float
    confidence: float


class CognitiveGraph:
    """
    The central cognitive graph.
    
    Responsible for node/edge management, activation state, 
    and providing the interface for reasoning operations.
    """

    def __init__(self, store: GraphStore) -> None:
        self.store = store
        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load nodes and edges from store into memory cache."""
        for node_data in self.store.list_nodes():
            node = Node.from_dict(node_data)
            self._nodes[node.id] = node
        
        for edge_data in self.store.list_edges():
            edge = Edge.from_dict(edge_data)
            self._edges[self._edge_key(edge.source, edge.target)] = edge

    def _edge_key(self, source: str, target: str) -> str:
        return f"{source}->{target}"

    # ── Node Management ───────────────────────────────────────────────────

    def add_node(self, node: Node) -> None:
        self._nodes[node.id] = node
        self.store.upsert_node(node.to_dict())

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            del self._nodes[node_id]
            self.store.delete_node(node_id)
            # Remove associated edges
            edges_to_remove = [k for k, e in self._edges.items() if e.source == node_id or e.target == node_id]
            for k in edges_to_remove:
                self.remove_edge(self._edges[k].source, self._edges[k].target)

    # ── Edge Management ───────────────────────────────────────────────────

    def add_edge(self, edge: Edge) -> None:
        key = self._edge_key(edge.source, edge.target)
        self._edges[key] = edge
        self.store.upsert_edge(edge.to_dict())

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        return self._edges.get(self._edge_key(source, target))

    def remove_edge(self, source: str, target: str) -> None:
        key = self._edge_key(source, target)
        if key in self._edges:
            del self._edges[key]
            self.store.delete_edge(source, target)

    # ── Activation State ──────────────────────────────────────────────────

    def propagate_activation(self, start_node_id: str, energy: float, decay: float = 0.5) -> None:
        """Simple spreading activation propagation."""
        node = self.get_node(start_node_id)
        if not node or energy < 0.01:
            return
        
        node.set_activation(node.activation + energy)
        
        # Propagate to neighbors
        for edge in self.get_outgoing_edges(start_node_id):
            # Energy scales by edge weight
            transfer = energy * edge.weight * decay
            self.propagate_activation(edge.target, transfer, decay)

    def apply_decay(self, rate: float = 0.01) -> None:
        """Apply temporal decay to all nodes and edges."""
        for node in self._nodes.values():
            node.set_activation(node.activation * (1.0 - rate))
        
        for edge in self._edges.values():
            edge.decay(rate)

    # ── Queries ───────────────────────────────────────────────────────────

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        return [e for e in self._edges.values() if e.source == node_id]

    def get_incoming_edges(self, node_id: str) -> List[Edge]:
        return [e for e in self._edges.values() if e.target == node_id]

    def get_neighbors(self, node_id: str) -> Set[str]:
        neighbors = set()
        for e in self.get_outgoing_edges(node_id):
            neighbors.add(edge.target)
        return neighbors

    def extract_subgraph(self, node_ids: Iterable[str]) -> CognitiveGraph:
        """Extract a subset of the graph as a new CognitiveGraph instance."""
        # Note: In-memory store for subgraph for now
        from .graph_store import InMemoryGraphStore
        sub_store = InMemoryGraphStore()
        sub_graph = CognitiveGraph(sub_store)
        
        node_id_set = set(node_ids)
        for nid in node_id_set:
            node = self.get_node(nid)
            if node:
                sub_graph.add_node(node)
        
        for edge in self._edges.values():
            if edge.source in node_id_set and edge.target in node_id_set:
                sub_graph.add_edge(edge)
        
        return sub_graph

    # ── Confidence Propagation ────────────────────────────────────────────

    def deduplicate(self) -> Dict[str, int]:
        """
        Merges nodes with identical semantic labels.
        """
        from encoder.concept_normalizer import ConceptNormalizer
        normalizer = ConceptNormalizer()
        
        merged_count = 0
        label_to_id: Dict[str, str] = {}
        to_merge: List[tuple[str, str]] = [] # (duplicate_id, primary_id)
        
        for node in list(self._nodes.values()):
            norm = normalizer.normalize(node.label)
            if norm in label_to_id:
                to_merge.append((node.id, label_to_id[norm]))
            else:
                label_to_id[norm] = node.id
                
        for dup_id, pri_id in to_merge:
            self._merge_nodes(dup_id, pri_id)
            merged_count += 1
            
        return {"nodes_merged": merged_count}

    def _merge_nodes(self, dup_id: str, pri_id: str) -> None:
        """Helper to merge two nodes."""
        pri_node = self._nodes[pri_id]
        dup_node = self._nodes[dup_id]
        
        # 1. Sum activation and access
        pri_node.activation = max(pri_node.activation, dup_node.activation)
        
        # 2. Redirect edges
        for edge in self.get_outgoing_edges(dup_id):
            edge.source = pri_id
            self.add_edge(edge)
            
        for edge in self.get_incoming_edges(dup_id):
            edge.target = pri_id
            self.add_edge(edge)
            
        # 3. Delete duplicate
        self.remove_node(dup_id)

    def promote_consensus(self, threshold: float = 0.8) -> int:
        """
        Promotes CORRELATES edges to CAUSES if they are strong and stable.
        """
        promoted = 0
        for edge in list(self._edges.values()):
            if edge.edge_type == EdgeType.CORRELATES:
                if edge.weight > threshold and edge.confidence > 0.7:
                    edge.edge_type = EdgeType.CAUSES
                    promoted += 1
                    self.store.upsert_edge(edge.to_dict())
        return promoted

    def propagate_confidence(self) -> None:
        """
        Re-calculate confidence scores based on structural patterns.
        (Implementation placeholder for specific reasoning logic)
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()]
        }

    def close(self) -> None:
        self.store.close()

    def count_nodes(self) -> int:
        return len(self._nodes)

    def count_edges(self) -> int:
        return len(self._edges)

    @property
    def store_kind(self) -> str:
        return type(self.store).__name__

    def get_node_label(self, node_id: str) -> str:
        node = self.get_node(node_id)
        return node.label if node else "Unknown"

    def get_node_by_label(self, label: str) -> Optional[Node]:
        node_id = hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]
        return self.get_node(node_id)

    def find_paths(self, source_label: str, target_label: str, max_hops: int = 5, max_paths: int = 20) -> List[PathMatch]:
        """Finds paths between two concept labels."""
        # Implementation placeholder
        return []

    def create_edge(self, source_label: str, target_label: str, edge_type: EdgeType, strength: float = 0.5) -> None:
        source_node = self.get_node_by_label(source_label)
        if not source_node:
            source_node = Node(id=hashlib.sha256(source_label.lower().strip().encode()).hexdigest()[:16], label=source_label)
            self.add_node(source_node)

        target_node = self.get_node_by_label(target_label)
        if not target_node:
            target_node = Node(id=hashlib.sha256(target_label.lower().strip().encode()).hexdigest()[:16], label=target_label)
            self.add_node(target_node)

        edge = Edge(source=source_node.id, target=target_node.id, edge_type=edge_type, weight=strength)
        self.add_edge(edge)


GraphEngine = CognitiveGraph
