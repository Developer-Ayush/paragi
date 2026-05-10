"""graph/graph.py — GraphEngine: the cognitive graph runtime.

Ported from app/graph.py with support for extended edge types.
This is the primary cognition layer — all reasoning happens here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from core.types import EdgeRecord, NodeRecord, make_edge_id, make_node_id, normalize_label, now_ts
from core.enums import EdgeType
from core.constants import (
    VECTOR_SIZE, EDGE_STRENGTH_FLOOR, EDGE_DECAY_PER_CYCLE, EDGE_PRUNE_THRESHOLD,
    ETA_DEFAULT, ALPHA_DEFAULT, BETA_DEFAULT,
)
from core.logger import get_logger
from graph.persistence.storage import GraphStore, HDF5GraphStore, InMemoryGraphStore

log = get_logger(__name__)

# Import BloomFilter from app (reuse existing)
try:
    from utils.bloom import BloomFilter  # type: ignore
except ImportError:
    BloomFilter = None  # type: ignore

SeedRelation = Tuple[str, str, EdgeType, float]


@dataclass(slots=True)
class PathMatch:
    node_ids: list[str]
    node_labels: list[str]
    edge_ids: list[str]
    edge_types: list[EdgeType]
    edge_strengths: list[float]
    hops: int
    mean_strength: float
    goal_relevance: float
    score: float


@dataclass(slots=True)
class ConsensusResult:
    source_label: str
    target_label: str
    path_count: int
    inferred_type: EdgeType
    upgraded: bool


@dataclass(slots=True)
class ContradictionResult:
    source_label: str
    positive_target: str
    negative_target: str
    positive_paths: int
    negative_paths: int
    verdict: str
    confidence: float
    minority_edge_weakened: bool


@dataclass(slots=True)
class HubNode:
    node_id: str
    node_label: str
    in_degree: int
    out_degree: int
    total_degree: int
    unique_neighbors: int
    edge_type_diversity: int
    access_count: int
    hub_score: float


@dataclass(slots=True)
class AnalogyCandidate:
    source_label: str
    candidate_label: str
    shared_neighbors: list[str]
    shared_count: int
    jaccard: float
    score: float


class GraphEngine:
    """
    The cognitive graph: the intelligence layer of Paragi.

    Nodes are concepts. Edges are typed semantic relations.
    Reasoning is graph traversal — no transformer token inference.
    """

    def __init__(
        self,
        store: GraphStore,
        bloom: object,
        bloom_path: Path,
        *,
        edge_strength_floor: float = EDGE_STRENGTH_FLOOR,
        edge_decay_per_cycle: float = EDGE_DECAY_PER_CYCLE,
        edge_prune_threshold: float = EDGE_PRUNE_THRESHOLD,
    ) -> None:
        self.store = store
        self.bloom = bloom
        self.bloom_path = bloom_path
        self.edge_strength_floor = edge_strength_floor
        self.edge_decay_per_cycle = edge_decay_per_cycle
        self.edge_prune_threshold = edge_prune_threshold
        self.store_kind = type(store).__name__

    @classmethod
    def build_default(cls, settings: object) -> "GraphEngine":
        """Build a GraphEngine from Settings."""
        s = settings  # type: ignore
        if BloomFilter is not None:
            bloom = (
                BloomFilter.load(s.bloom_path)
                if s.bloom_path.exists()
                else BloomFilter(capacity=s.bloom_capacity, error_rate=s.bloom_error_rate)
            )
        else:
            bloom = _FakeBloom()

        store: GraphStore
        if s.prefer_hdf5:
            try:
                store = HDF5GraphStore(s.hdf5_path)
            except Exception as e:
                raise RuntimeError(f"Failed to init HDF5 storage: {e}")
        else:
            store = InMemoryGraphStore()

        engine = cls(
            store=store, bloom=bloom, bloom_path=s.bloom_path,
            edge_strength_floor=s.edge_strength_floor,
            edge_decay_per_cycle=s.edge_decay_per_cycle,
            edge_prune_threshold=s.edge_prune_threshold,
        )
        engine._rebuild_bloom_if_needed()
        return engine

    # ── Bloom helpers ──────────────────────────────────────────────────────

    def _persist_bloom(self) -> None:
        if BloomFilter is not None and hasattr(self.bloom, "save"):
            self.bloom.save(self.bloom_path)

    def _rebuild_bloom_if_needed(self) -> None:
        if self.bloom_path.exists():
            return
        for node_id in self.store.iter_node_ids():
            if hasattr(self.bloom, "add"):
                self.bloom.add(node_id)
        self._persist_bloom()

    # ── Node operations ────────────────────────────────────────────────────

    def create_or_get_node(self, label: str) -> NodeRecord:
        normalized = normalize_label(label)
        node_id = make_node_id(normalized)
        ts = now_ts()

        if node_id not in self.bloom:
            node = NodeRecord(id=node_id, label=normalized, created=ts, last_accessed=ts, access_count=1)
            self.store.upsert_node(node)
            if hasattr(self.bloom, "add"):
                self.bloom.add(node_id)
            self._persist_bloom()
            return node

        existing = self.store.get_node(node_id)
        if existing is not None:
            updated = NodeRecord(
                id=existing.id, label=existing.label, created=existing.created,
                last_accessed=ts, access_count=existing.access_count + 1,
            )
            return self.store.upsert_node(updated)

        node = NodeRecord(id=node_id, label=normalized, created=ts, last_accessed=ts, access_count=1)
        self.store.upsert_node(node)
        if hasattr(self.bloom, "add"):
            self.bloom.add(node_id)
        self._persist_bloom()
        return node

    def node_exists(self, label: str) -> bool:
        node_id = make_node_id(normalize_label(label))
        if node_id not in self.bloom:
            return False
        return self.store.get_node(node_id) is not None

    def get_node_by_label(self, label: str) -> NodeRecord | None:
        node_id = make_node_id(normalize_label(label))
        if node_id not in self.bloom:
            return None
        return self.store.get_node(node_id)

    def get_node_label(self, node_id: str) -> str:
        node = self.store.get_node(node_id)
        return node.label if node is not None else node_id

    # ── Edge operations ────────────────────────────────────────────────────

    def create_edge(
        self,
        source_label: str,
        target_label: str,
        edge_type: EdgeType = EdgeType.CORRELATES,
        *,
        strength: float = 0.1,
        vector: Sequence[float] | None = None,
        emotional_weight: float = 0.0,
        stability: float = 1.0,
        confidence: float = 0.5,
    ) -> EdgeRecord:
        source = self.create_or_get_node(source_label)
        target = self.create_or_get_node(target_label)
        edge_id = make_edge_id(source.id, target.id)
        ts = now_ts()
        edge_vector = list(vector) if vector is not None else [0.0] * VECTOR_SIZE
        if len(edge_vector) != VECTOR_SIZE:
            edge_vector = (edge_vector + [0.0] * VECTOR_SIZE)[:VECTOR_SIZE]

        existing = self.store.get_edge(edge_id)
        edge_type_val = edge_type.value if isinstance(edge_type, EdgeType) else str(edge_type)
        if existing is not None:
            merged = EdgeRecord(
                id=existing.id, source=existing.source, target=existing.target,
                type=edge_type_val, vector=edge_vector,
                strength=max(existing.strength, strength),
                emotional_weight=emotional_weight, recall_count=existing.recall_count,
                stability=stability, last_activated=ts, created=existing.created,
                confidence=max(existing.confidence, confidence),
            )
            return self.store.upsert_edge(merged)

        edge = EdgeRecord(
            id=edge_id, source=source.id, target=target.id,
            type=edge_type_val, vector=edge_vector,
            strength=float(strength), emotional_weight=float(emotional_weight),
            recall_count=0, stability=float(stability),
            last_activated=ts, created=ts, confidence=float(confidence),
        )
        return self.store.upsert_edge(edge)

    def get_edge(self, source_label: str, target_label: str) -> EdgeRecord | None:
        source_id = make_node_id(normalize_label(source_label))
        target_id = make_node_id(normalize_label(target_label))
        return self.store.get_edge(make_edge_id(source_id, target_id))

    def get_edge_by_id(self, edge_id: str) -> EdgeRecord | None:
        return self.store.get_edge(edge_id)

    def get_neighbors(self, label: str) -> List[EdgeRecord]:
        node_id = make_node_id(normalize_label(label))
        node = self.store.get_node(node_id)
        return [] if node is None else self.store.list_outgoing(node.id)

    def strengthen_edge(self, edge_id: str) -> EdgeRecord | None:
        edge = self.store.get_edge(edge_id)
        if edge is None:
            return None
        eta = edge.vector[850] if len(edge.vector) > 850 else ETA_DEFAULT
        decay_param = edge.vector[900] if len(edge.vector) > 900 else EDGE_DECAY_PER_CYCLE
        s = edge.emotional_weight
        r = float(edge.recall_count)
        rule_delta = eta * (s - edge.strength) + (ALPHA_DEFAULT * r) - (BETA_DEFAULT * decay_param)
        next_strength = max(self.edge_strength_floor, min(1.0, edge.strength + rule_delta))
        self.store.update_edge_strength(edge_id, next_strength, increment_recall=True)
        return self.store.get_edge(edge_id)

    def weaken_edge(self, edge_id: str, factor: float = 0.9) -> EdgeRecord | None:
        edge = self.store.get_edge(edge_id)
        if edge is None:
            return None
        next_strength = max(self.edge_strength_floor, edge.strength * factor)
        self.store.update_edge_strength(edge_id, next_strength, increment_recall=False)
        return self.store.get_edge(edge_id)

    def decay_all_edges(self) -> int:
        count = 0
        base_decay = self.edge_decay_per_cycle
        for edge_id in self.store.list_edge_ids():
            edge = self.store.get_edge(edge_id)
            if edge is None:
                continue
            next_strength = self.edge_strength_floor + (
                edge.strength - self.edge_strength_floor
            ) * math.exp(-base_decay)
            new_vector = list(edge.vector)
            for i in range(len(new_vector)):
                if 175 <= i <= 209:
                    rate = base_decay * 0.1
                elif 580 <= i <= 639:
                    rate = base_decay * 2.0
                else:
                    rate = base_decay
                new_vector[i] = new_vector[i] * (1.0 - rate)
            updated = EdgeRecord(
                id=edge.id, source=edge.source, target=edge.target,
                type=edge.type, vector=new_vector, strength=next_strength,
                emotional_weight=edge.emotional_weight, recall_count=edge.recall_count,
                stability=edge.stability, last_activated=edge.last_activated,
                created=edge.created, confidence=edge.confidence,
            )
            self.store.upsert_edge(updated)
            count += 1
        return count

    # ── Graph statistics ───────────────────────────────────────────────────

    def count_nodes(self) -> int:
        return len(list(self.store.iter_node_ids()))

    def count_edges(self) -> int:
        return len(self.store.list_edge_ids())

    def list_nodes(self, *, limit: int = 200) -> list[NodeRecord]:
        items: list[NodeRecord] = []
        for node_id in self.store.iter_node_ids():
            node = self.store.get_node(node_id)
            if node is not None:
                items.append(node)
        items.sort(key=lambda n: (-n.access_count, -n.last_accessed, n.label))
        return items[:limit]

    def list_edges(self, *, limit: int = 200, min_strength: float = 0.0, sort_by: str = "recent") -> list[EdgeRecord]:
        all_edges = self._all_edges()
        items = [e for e in all_edges if e.strength >= min_strength]
        if sort_by == "strength":
            items.sort(key=lambda e: (-e.strength, -e.created, e.id))
        else:
            items.sort(key=lambda e: (-e.created, -e.strength, e.id))
        return items[:limit]

    def _all_edges(self) -> list[EdgeRecord]:
        items = []
        for edge_id in self.store.list_edge_ids():
            edge = self.store.get_edge(edge_id)
            if edge is not None:
                items.append(edge)
        return items

    # ── Path finding ───────────────────────────────────────────────────────

    def find_paths(
        self,
        source_label: str,
        target_label: str,
        *,
        max_hops: int = 7,
        max_paths: int = 64,
        goal_relevance: float = 1.0,
        edge_type_filter: list[str] | None = None,
    ) -> List[PathMatch]:
        source = self.get_node_by_label(source_label)
        target = self.get_node_by_label(target_label)
        if source is None or target is None:
            return []

        results: list[PathMatch] = []
        visited = {source.id}
        path_node_ids: list[str] = [source.id]
        path_edges: list[EdgeRecord] = []

        def dfs(current_node_id: str) -> None:
            if len(results) >= max_paths:
                return
            if current_node_id == target.id and path_edges:
                strengths = [e.strength for e in path_edges]
                mean_strength = sum(strengths) / len(strengths)
                results.append(PathMatch(
                    node_ids=list(path_node_ids),
                    node_labels=[self.get_node_label(nid) for nid in path_node_ids],
                    edge_ids=[e.id for e in path_edges],
                    edge_types=[e.type for e in path_edges],
                    edge_strengths=strengths,
                    hops=len(path_edges),
                    mean_strength=mean_strength,
                    goal_relevance=goal_relevance,
                    score=mean_strength * goal_relevance,
                ))
                return
            if len(path_edges) >= max_hops:
                return
            for edge in self.store.list_outgoing(current_node_id):
                if edge_type_filter and edge.type not in edge_type_filter:
                    continue
                next_id = edge.target
                if next_id in visited:
                    continue
                visited.add(next_id)
                path_node_ids.append(next_id)
                path_edges.append(edge)
                dfs(next_id)
                path_edges.pop()
                path_node_ids.pop()
                visited.remove(next_id)
                if len(results) >= max_paths:
                    return

        dfs(source.id)
        results.sort(key=lambda p: (-p.score, p.hops, -p.mean_strength))
        return results[:max_paths]

    # ── Consensus & Contradiction ──────────────────────────────────────────

    def path_consensus(
        self, source_label: str, target_label: str,
        *, max_hops: int = 7, max_paths: int = 64,
        cause_threshold: int = 3, auto_upgrade: bool = True,
    ) -> ConsensusResult:
        paths = self.find_paths(source_label, target_label, max_hops=max_hops, max_paths=max_paths)
        path_count = len(paths)
        if path_count >= cause_threshold:
            inferred = EdgeType.CAUSES
        elif path_count >= 1:
            inferred = EdgeType.CORRELATES
        else:
            inferred = EdgeType.INFERRED

        upgraded = False
        if auto_upgrade and path_count >= 1:
            existing = self.get_edge(source_label, target_label)
            if existing is None:
                self.create_edge(source_label, target_label, inferred, strength=0.25)
                upgraded = True

        return ConsensusResult(
            source_label=normalize_label(source_label),
            target_label=normalize_label(target_label),
            path_count=path_count,
            inferred_type=inferred,
            upgraded=upgraded,
        )

    def contradiction_vote(
        self, source_label: str, positive_target: str, negative_target: str,
        *, max_hops: int = 7, max_paths: int = 64, weaken_factor: float = 0.9,
    ) -> ContradictionResult:
        pos_paths = self.find_paths(source_label, positive_target, max_hops=max_hops, max_paths=max_paths)
        neg_paths = self.find_paths(source_label, negative_target, max_hops=max_hops, max_paths=max_paths)
        pos_count, neg_count = len(pos_paths), len(neg_paths)
        total = pos_count + neg_count

        verdict, confidence, minority_weakened = "UNKNOWN", 0.0, False
        if total == 0:
            pass
        elif pos_count == neg_count:
            verdict, confidence = "TIE", 0.5
        elif pos_count > neg_count:
            verdict = normalize_label(positive_target)
            confidence = pos_count / total
            minority = self.get_edge(source_label, negative_target)
            if minority:
                self.weaken_edge(minority.id, factor=weaken_factor)
                minority_weakened = True
        else:
            verdict = normalize_label(negative_target)
            confidence = neg_count / total
            minority = self.get_edge(source_label, positive_target)
            if minority:
                self.weaken_edge(minority.id, factor=weaken_factor)
                minority_weakened = True

        return ContradictionResult(
            source_label=normalize_label(source_label),
            positive_target=normalize_label(positive_target),
            negative_target=normalize_label(negative_target),
            positive_paths=pos_count, negative_paths=neg_count,
            verdict=verdict, confidence=confidence,
            minority_edge_weakened=minority_weakened,
        )

    # ── Analogy ────────────────────────────────────────────────────────────

    def find_analogy_candidates(
        self, source_label: str, *, limit: int = 10, min_shared_neighbors: int = 2,
    ) -> List[AnalogyCandidate]:
        source = self.get_node_by_label(source_label)
        if source is None:
            return []
        _, _, _, _, neighbors, _ = self._build_centrality_indexes()
        source_neighbors = neighbors.get(source.id, set())
        if not source_neighbors:
            return []

        items: list[AnalogyCandidate] = []
        for candidate_id in list(self.store.iter_node_ids()):
            if candidate_id == source.id:
                continue
            candidate_neighbors = neighbors.get(candidate_id, set())
            shared_ids = source_neighbors & candidate_neighbors
            shared_count = len(shared_ids)
            if shared_count < min_shared_neighbors:
                continue
            union_count = len(source_neighbors | candidate_neighbors)
            jaccard = shared_count / union_count if union_count > 0 else 0.0
            shared_labels = sorted(self.get_node_label(nid) for nid in shared_ids)
            items.append(AnalogyCandidate(
                source_label=source.label,
                candidate_label=self.get_node_label(candidate_id),
                shared_neighbors=shared_labels[:8],
                shared_count=shared_count,
                jaccard=jaccard,
                score=shared_count + (2.0 * jaccard),
            ))

        items.sort(key=lambda i: (-i.score, -i.shared_count, i.candidate_label))
        return items[:limit]

    # ── Hub detection ──────────────────────────────────────────────────────

    def detect_hubs(self, *, limit: int = 20, min_total_degree: int = 2, min_edge_type_diversity: int = 1) -> List[HubNode]:
        node_ids = list(self.store.iter_node_ids())
        if not node_ids:
            return []
        incoming, outgoing, inc_str, out_str, neighbors, edge_types = self._build_centrality_indexes()
        hubs: list[HubNode] = []
        for node_id in node_ids:
            node = self.store.get_node(node_id)
            if node is None:
                continue
            in_d = int(incoming.get(node_id, 0))
            out_d = int(outgoing.get(node_id, 0))
            total = in_d + out_d
            if total < min_total_degree:
                continue
            diversity = len(edge_types.get(node_id, set()))
            if diversity < min_edge_type_diversity:
                continue
            unique = len(neighbors.get(node_id, set()))
            wa = float(inc_str.get(node_id, 0.0) + out_str.get(node_id, 0.0))
            hub_score = total + (0.75 * unique) + (1.5 * diversity) + (0.5 * wa) + min(node.access_count, 1000) * 0.01
            hubs.append(HubNode(
                node_id=node.id, node_label=node.label,
                in_degree=in_d, out_degree=out_d, total_degree=total,
                unique_neighbors=unique, edge_type_diversity=diversity,
                access_count=node.access_count, hub_score=hub_score,
            ))
        hubs.sort(key=lambda h: (-h.hub_score, -h.total_degree, h.node_label))
        return hubs[:limit]

    def _build_centrality_indexes(self):
        from collections import defaultdict
        incoming: Dict[str, int] = defaultdict(int)
        outgoing: Dict[str, int] = defaultdict(int)
        inc_str: Dict[str, float] = defaultdict(float)
        out_str: Dict[str, float] = defaultdict(float)
        neighbors: Dict[str, set] = defaultdict(set)
        edge_types: Dict[str, set] = defaultdict(set)
        for edge in self._all_edges():
            outgoing[edge.source] += 1
            incoming[edge.target] += 1
            out_str[edge.source] += edge.strength
            inc_str[edge.target] += edge.strength
            neighbors[edge.source].add(edge.target)
            neighbors[edge.target].add(edge.source)
            edge_types[edge.source].add(edge.type)
            edge_types[edge.target].add(edge.type)
        return incoming, outgoing, inc_str, out_str, neighbors, edge_types

    # ── Bootstrap ─────────────────────────────────────────────────────────

    def bootstrap(self, relations: Iterable[SeedRelation]) -> int:
        created = 0
        for source, target, edge_type, strength in relations:
            if self.create_edge(source, target, edge_type, strength=strength):
                created += 1
        return created

    def bootstrap_default(self) -> int:
        seeds: list[SeedRelation] = [
            ("gravity", "earth", EdgeType.CORRELATES, 0.95),
            ("earth", "round", EdgeType.IS_A, 0.90),
        ]
        return self.bootstrap(seeds)

    def prune_edges(self, threshold: float | None = None) -> int:
        if threshold is None:
            threshold = self.edge_prune_threshold
        count = 0
        for edge_id in self.store.list_edge_ids():
            edge = self.store.get_edge(edge_id)
            if edge is not None and edge.strength < threshold:
                self.store.delete_edge(edge_id)
                count += 1
        return count

    def deduplicate_graph(self, semantic_threshold: float = 0.95) -> Dict[str, int]:
        """Merge semantically similar nodes and identical labels."""
        nodes_merged = 0
        repointed_count = 0
        
        # 1. Merge identical labels
        ids = list(self.store.iter_node_ids())
        label_to_ids: Dict[str, List[str]] = {}
        for nid in ids:
            label = normalize_label(self.get_node_label(nid))
            label_to_ids.setdefault(label, []).append(nid)
            
        for label, group in label_to_ids.items():
            if len(group) > 1:
                # Merge into the oldest one (or just the first)
                target_id = group[0]
                for nid in group[1:]:
                    print(f"DEBUG_DEDUP: Merging identical label '{label}' ({nid} -> {target_id})")
                    repointed_count += self._merge_nodes(nid, target_id)
                    nodes_merged += 1
                    
        # 2. Semantic merge if threshold is low enough
        if semantic_threshold < 0.99 and len(ids) > 1:
            # Simple O(N^2) merge for small graphs (tests)
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    id1, id2 = ids[i], ids[j]
                    if id1 not in self.store.iter_node_ids() or id2 not in self.store.iter_node_ids():
                        continue
                    
                    from encoder.semantic_encoder import EmbeddingEncoder
                    encoder = EmbeddingEncoder()
                    
                    label1 = self.get_node_label(id1)
                    label2 = self.get_node_label(id2)
                    v1 = encoder.encode(label1.split(), label1).semantic_vector
                    v2 = encoder.encode(label2.split(), label2).semantic_vector
                    if not v1 or not v2: continue
                    
                    # Cosine similarity
                    dot = sum(a*b for a,b in zip(v1, v2))
                    mag1 = math.sqrt(sum(a*a for a in v1))
                    mag2 = math.sqrt(sum(b*b for b in v2))
                    sim = dot / (mag1 * mag2) if mag1 * mag2 > 0 else 0
                    
                    if sim >= semantic_threshold:
                        print(f"DEBUG_DEDUP: Semantic merge (sim={sim:.2f}) '{self.get_node_label(id2)}' -> '{self.get_node_label(id1)}'")
                        repointed_count += self._merge_nodes(id2, id1)
                        nodes_merged += 1
            
        return {"nodes_merged": nodes_merged, "edges_repointed": repointed_count}
        
    def _merge_nodes(self, source_id: str, target_id: str) -> int:
        repointed = 0
        # Outgoing
        for edge in self.store.list_outgoing(source_id):
            new_edge = EdgeRecord(
                id=make_edge_id(target_id, edge.target),
                source=target_id, target=edge.target,
                type=edge.type, vector=edge.vector,
                strength=edge.strength, created=edge.created,
                emotional_weight=edge.emotional_weight, recall_count=edge.recall_count,
                stability=edge.stability, last_activated=edge.last_activated,
                confidence=edge.confidence
            )
            self.store.upsert_edge(new_edge)
            self.store.delete_edge(edge.id)
            repointed += 1
            
        # Incoming
        for edge in self.store.list_incoming(source_id):
            new_edge = EdgeRecord(
                id=make_edge_id(edge.source, target_id),
                source=edge.source, target=target_id,
                type=edge.type, vector=edge.vector,
                strength=edge.strength, created=edge.created,
                emotional_weight=edge.emotional_weight, recall_count=edge.recall_count,
                stability=edge.stability, last_activated=edge.last_activated,
                confidence=edge.confidence
            )
            self.store.upsert_edge(new_edge)
            self.store.delete_edge(edge.id)
            repointed += 1
            
        self.store.delete_node(source_id)
        return repointed

    def close(self) -> None:
        self.store.close()


class _FakeBloom:
    """Fallback when app.bloom is unavailable."""
    def __init__(self):
        self._set = set()
    def __contains__(self, item: str) -> bool:
        return item in self._set
    def add(self, item: str) -> None:
        self._set.add(item)
    def save(self, path: object) -> None:
        pass
