from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .bloom import BloomFilter
from .config import Settings
from .models import EdgeRecord, EdgeType, NodeRecord, make_edge_id, make_node_id, normalize_label, now_ts
from .storage import GraphStore, HDF5GraphStore, InMemoryGraphStore

VECTOR_SIZE = 1024
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
    def __init__(
        self,
        store: GraphStore,
        bloom: BloomFilter,
        bloom_path: Path,
        *,
        edge_strength_floor: float,
        edge_decay_per_cycle: float,
    ) -> None:
        self.store = store
        self.bloom = bloom
        self.bloom_path = bloom_path
        self.edge_strength_floor = edge_strength_floor
        self.edge_decay_per_cycle = edge_decay_per_cycle
        self.store_kind = type(store).__name__

    @classmethod
    def build_default(cls, settings: Settings) -> "GraphEngine":
        bloom = BloomFilter.load(settings.bloom_path) if settings.bloom_path.exists() else BloomFilter(
            capacity=settings.bloom_capacity,
            error_rate=settings.bloom_error_rate,
        )

        store: GraphStore
        if settings.prefer_hdf5:
            try:
                store = HDF5GraphStore(settings.hdf5_path)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize HDF5 storage as requested: {e}")
        else:
            store = InMemoryGraphStore()

        engine = cls(
            store=store,
            bloom=bloom,
            bloom_path=settings.bloom_path,
            edge_strength_floor=settings.edge_strength_floor,
            edge_decay_per_cycle=settings.edge_decay_per_cycle,
        )
        engine._rebuild_bloom_if_needed()
        return engine

    def _persist_bloom(self) -> None:
        self.bloom.save(self.bloom_path)

    def _rebuild_bloom_if_needed(self) -> None:
        if self.bloom_path.exists():
            return
        for node_id in self.store.iter_node_ids():
            self.bloom.add(node_id)
        self._persist_bloom()

    def create_or_get_node(self, label: str) -> NodeRecord:
        normalized = normalize_label(label)
        node_id = make_node_id(normalized)
        ts = now_ts()

        if node_id not in self.bloom:
            node = NodeRecord(
                id=node_id,
                label=normalized,
                created=ts,
                last_accessed=ts,
                access_count=1,
            )
            self.store.upsert_node(node)
            self.bloom.add(node_id)
            self._persist_bloom()
            return node

        existing = self.store.get_node(node_id)
        if existing is not None:
            updated = NodeRecord(
                id=existing.id,
                label=existing.label,
                created=existing.created,
                last_accessed=ts,
                access_count=existing.access_count + 1,
            )
            return self.store.upsert_node(updated)

        # Bloom false-positive or missing in store
        node = NodeRecord(
            id=node_id,
            label=normalized,
            created=ts,
            last_accessed=ts,
            access_count=1,
        )
        self.store.upsert_node(node)
        self.bloom.add(node_id)
        self._persist_bloom()
        return node

    def node_exists(self, label: str) -> bool:
        node_id = make_node_id(normalize_label(label))
        if node_id not in self.bloom:
            return False
        return self.store.get_node(node_id) is not None

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
    ) -> EdgeRecord:
        source = self.create_or_get_node(source_label)
        target = self.create_or_get_node(target_label)
        edge_id = make_edge_id(source.id, target.id)
        ts = now_ts()
        edge_vector = list(vector) if vector is not None else [0.0] * VECTOR_SIZE
        if len(edge_vector) != VECTOR_SIZE:
            raise ValueError(f"vector must have length {VECTOR_SIZE}")

        existing = self.store.get_edge(edge_id)
        if existing is not None:
            merged = EdgeRecord(
                id=existing.id,
                source=existing.source,
                target=existing.target,
                type=edge_type,
                vector=edge_vector,
                strength=max(existing.strength, strength),
                emotional_weight=emotional_weight,
                recall_count=existing.recall_count,
                stability=stability,
                last_activated=ts,
                created=existing.created,
            )
            return self.store.upsert_edge(merged)

        edge = EdgeRecord(
            id=edge_id,
            source=source.id,
            target=target.id,
            type=edge_type,
            vector=edge_vector,
            strength=float(strength),
            emotional_weight=float(emotional_weight),
            recall_count=0,
            stability=float(stability),
            last_activated=ts,
            created=ts,
        )
        return self.store.upsert_edge(edge)

    def get_edge(self, source_label: str, target_label: str) -> EdgeRecord | None:
        source_id = make_node_id(normalize_label(source_label))
        target_id = make_node_id(normalize_label(target_label))
        edge_id = make_edge_id(source_id, target_id)
        return self.store.get_edge(edge_id)

    def get_edge_by_id(self, edge_id: str) -> EdgeRecord | None:
        return self.store.get_edge(edge_id)

    def strengthen_edge(self, edge_id: str) -> EdgeRecord | None:
        edge = self.store.get_edge(edge_id)
        if edge is None:
            return None

        # Paper's §5.3 update rule: Δstrength = η(S - strength) + αR - βD
        # η (learning rate) at vector[850], D (decay rate) at vector[900]
        # S (emotional modulation) = emotional_weight
        # R (recall) = current recall_count
        eta = edge.vector[850] if len(edge.vector) > 850 else 0.1
        decay_param = edge.vector[900] if len(edge.vector) > 900 else 0.005
        s = edge.emotional_weight
        r = float(edge.recall_count)

        alpha = 0.01
        beta = 0.005

        # Calculate rule-based delta
        rule_delta = eta * (s - edge.strength) + (alpha * r) - (beta * decay_param)

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

            # 1. Decay the main strength using exponential floor formula:
            # strength(t) = floor + (initial - floor) * e^(-decay_rate * t)
            # For one cycle: next = floor + (current - floor) * exp(-base_decay)
            next_strength = self.edge_strength_floor + (edge.strength - self.edge_strength_floor) * math.exp(-base_decay)

            # 2. Decay the 1024-dim vector with per-dimension rates (§5.3)
            # Range 175–209 (Emotional): slowest
            # Range 580–639 (Factual): fastest
            new_vector = list(edge.vector)
            for i in range(len(new_vector)):
                if 175 <= i <= 209:
                    rate = base_decay * 0.1
                elif 580 <= i <= 639:
                    rate = base_decay * 2.0
                else:
                    rate = base_decay
                new_vector[i] = new_vector[i] * (1.0 - rate)

            # 3. Persist updated edge
            updated_edge = EdgeRecord(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                type=edge.type,
                vector=new_vector,
                strength=next_strength,
                emotional_weight=edge.emotional_weight,
                recall_count=edge.recall_count,
                stability=edge.stability,
                last_activated=edge.last_activated,
                created=edge.created,
            )
            self.store.upsert_edge(updated_edge)
            count += 1
        return count

    def get_neighbors(self, label: str) -> List[EdgeRecord]:
        node_id = make_node_id(normalize_label(label))
        node = self.store.get_node(node_id)
        if node is None:
            return []
        return self.store.list_outgoing(node.id)

    def _get_node_by_label(self, label: str) -> NodeRecord | None:
        node_id = make_node_id(normalize_label(label))
        if node_id not in self.bloom:
            return None
        return self.store.get_node(node_id)

    def _label_for_node_id(self, node_id: str) -> str:
        node = self.store.get_node(node_id)
        if node is None:
            return node_id
        return node.label

    def get_node_label(self, node_id: str) -> str:
        return self._label_for_node_id(node_id)

    def _all_edges(self) -> list[EdgeRecord]:
        items: list[EdgeRecord] = []
        for edge_id in self.store.list_edge_ids():
            edge = self.store.get_edge(edge_id)
            if edge is not None:
                items.append(edge)
        return items

    def count_nodes(self) -> int:
        return len(list(self.store.iter_node_ids()))

    def count_edges(self) -> int:
        return len(self.store.list_edge_ids())

    def list_nodes(self, *, limit: int = 200) -> list[NodeRecord]:
        if limit <= 0:
            return []
        items: list[NodeRecord] = []
        for node_id in self.store.iter_node_ids():
            node = self.store.get_node(node_id)
            if node is not None:
                items.append(node)
        items.sort(key=lambda node: (-node.access_count, -node.last_accessed, node.label))
        return items[:limit]

    def list_edges(self, *, limit: int = 200, min_strength: float = 0.0, sort_by: str = "recent") -> list[EdgeRecord]:
        if limit <= 0:
            return []
        min_strength = float(max(0.0, min(1.0, min_strength)))
        items = [edge for edge in self._all_edges() if edge.strength >= min_strength]
        if sort_by == "strength":
            items.sort(key=lambda edge: (-edge.strength, -edge.created, edge.id))
        else:
            items.sort(key=lambda edge: (-edge.created, -edge.strength, edge.id))
        return items[:limit]

    def _build_centrality_indexes(self) -> tuple[
        Dict[str, int],
        Dict[str, int],
        Dict[str, float],
        Dict[str, float],
        Dict[str, set[str]],
        Dict[str, set[EdgeType]],
    ]:
        incoming: Dict[str, int] = defaultdict(int)
        outgoing: Dict[str, int] = defaultdict(int)
        incoming_strength: Dict[str, float] = defaultdict(float)
        outgoing_strength: Dict[str, float] = defaultdict(float)
        neighbors: Dict[str, set[str]] = defaultdict(set)
        edge_types: Dict[str, set[EdgeType]] = defaultdict(set)

        for edge in self._all_edges():
            outgoing[edge.source] += 1
            incoming[edge.target] += 1
            outgoing_strength[edge.source] += edge.strength
            incoming_strength[edge.target] += edge.strength

            neighbors[edge.source].add(edge.target)
            neighbors[edge.target].add(edge.source)
            edge_types[edge.source].add(edge.type)
            edge_types[edge.target].add(edge.type)

        return incoming, outgoing, incoming_strength, outgoing_strength, neighbors, edge_types

    def detect_hubs(
        self,
        *,
        limit: int = 20,
        min_total_degree: int = 2,
        min_edge_type_diversity: int = 1,
    ) -> List[HubNode]:
        if limit <= 0:
            return []

        node_ids = list(self.store.iter_node_ids())
        if not node_ids:
            return []

        incoming, outgoing, incoming_strength, outgoing_strength, neighbors, edge_types = self._build_centrality_indexes()

        hubs: list[HubNode] = []
        for node_id in node_ids:
            node = self.store.get_node(node_id)
            if node is None:
                continue

            in_degree = int(incoming.get(node_id, 0))
            out_degree = int(outgoing.get(node_id, 0))
            total_degree = in_degree + out_degree
            if total_degree < min_total_degree:
                continue

            edge_type_diversity = len(edge_types.get(node_id, set()))
            if edge_type_diversity < min_edge_type_diversity:
                continue

            unique_neighbors = len(neighbors.get(node_id, set()))
            weighted_activity = float(incoming_strength.get(node_id, 0.0) + outgoing_strength.get(node_id, 0.0))
            access_bonus = min(node.access_count, 1000) * 0.01
            hub_score = (
                total_degree
                + (0.75 * unique_neighbors)
                + (1.5 * edge_type_diversity)
                + (0.5 * weighted_activity)
                + access_bonus
            )

            hubs.append(
                HubNode(
                    node_id=node.id,
                    node_label=node.label,
                    in_degree=in_degree,
                    out_degree=out_degree,
                    total_degree=total_degree,
                    unique_neighbors=unique_neighbors,
                    edge_type_diversity=edge_type_diversity,
                    access_count=node.access_count,
                    hub_score=hub_score,
                )
            )

        hubs.sort(key=lambda item: (-item.hub_score, -item.total_degree, item.node_label))
        return hubs[:limit]

    def find_analogy_candidates(
        self,
        source_label: str,
        *,
        limit: int = 10,
        min_shared_neighbors: int = 2,
    ) -> List[AnalogyCandidate]:
        if limit <= 0:
            return []

        source = self._get_node_by_label(source_label)
        if source is None:
            return []

        node_ids = list(self.store.iter_node_ids())
        if not node_ids:
            return []

        _, _, _, _, neighbors, _ = self._build_centrality_indexes()
        source_neighbors = neighbors.get(source.id, set())
        if not source_neighbors:
            return []

        items: list[AnalogyCandidate] = []
        for candidate_id in node_ids:
            if candidate_id == source.id:
                continue
            candidate_neighbors = neighbors.get(candidate_id, set())
            if not candidate_neighbors:
                continue

            shared_ids = source_neighbors.intersection(candidate_neighbors)
            shared_count = len(shared_ids)
            if shared_count < min_shared_neighbors:
                continue

            union_count = len(source_neighbors.union(candidate_neighbors))
            jaccard = (shared_count / union_count) if union_count > 0 else 0.0
            shared_labels = sorted(self._label_for_node_id(node_id) for node_id in shared_ids)
            score = shared_count + (2.0 * jaccard)

            items.append(
                AnalogyCandidate(
                    source_label=source.label,
                    candidate_label=self._label_for_node_id(candidate_id),
                    shared_neighbors=shared_labels[:8],
                    shared_count=shared_count,
                    jaccard=jaccard,
                    score=score,
                )
            )

        items.sort(key=lambda item: (-item.score, -item.shared_count, item.candidate_label))
        return items[:limit]

    def find_paths(
        self,
        source_label: str,
        target_label: str,
        *,
        max_hops: int = 7,
        max_paths: int = 64,
        goal_relevance: float = 1.0,
    ) -> List[PathMatch]:
        source = self._get_node_by_label(source_label)
        target = self._get_node_by_label(target_label)
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
                strengths = [edge.strength for edge in path_edges]
                mean_strength = sum(strengths) / len(strengths)
                score = mean_strength * goal_relevance
                results.append(
                    PathMatch(
                        node_ids=list(path_node_ids),
                        node_labels=[self._label_for_node_id(node_id) for node_id in path_node_ids],
                        edge_ids=[edge.id for edge in path_edges],
                        edge_types=[edge.type for edge in path_edges],
                        edge_strengths=strengths,
                        hops=len(path_edges),
                        mean_strength=mean_strength,
                        goal_relevance=goal_relevance,
                        score=score,
                    )
                )
                return

            if len(path_edges) >= max_hops:
                return

            for edge in self.store.list_outgoing(current_node_id):
                next_node_id = edge.target
                if next_node_id in visited:
                    continue

                visited.add(next_node_id)
                path_node_ids.append(next_node_id)
                path_edges.append(edge)
                dfs(next_node_id)
                path_edges.pop()
                path_node_ids.pop()
                visited.remove(next_node_id)

                if len(results) >= max_paths:
                    return

        dfs(source.id)
        results.sort(key=lambda p: (-p.score, p.hops, -p.mean_strength))
        return results[:max_paths]

    def _edge_type_rank(self, edge_type: EdgeType) -> int:
        rank_map = {
            EdgeType.CORRELATES: 1,
            EdgeType.INFERRED: 2,
            EdgeType.CAUSES: 3,
            EdgeType.IS_A: 3,
            EdgeType.TEMPORAL: 2,
        }
        return rank_map.get(edge_type, 0)

    def path_consensus(
        self,
        source_label: str,
        target_label: str,
        *,
        max_hops: int = 7,
        max_paths: int = 64,
        cause_threshold: int = 3,
        auto_upgrade: bool = True,
    ) -> ConsensusResult:
        paths = self.find_paths(source_label, target_label, max_hops=max_hops, max_paths=max_paths)
        path_count = len(paths)

        if path_count >= cause_threshold:
            inferred_type = EdgeType.CAUSES
        elif path_count >= 1:
            inferred_type = EdgeType.CORRELATES
        else:
            inferred_type = EdgeType.INFERRED

        upgraded = False
        if auto_upgrade and path_count >= 1:
            existing = self.get_edge(source_label, target_label)
            if existing is None:
                self.create_edge(source_label, target_label, inferred_type, strength=0.25)
                upgraded = True
            elif self._edge_type_rank(inferred_type) > self._edge_type_rank(existing.type):
                self.create_edge(source_label, target_label, inferred_type, strength=existing.strength)
                upgraded = True

        return ConsensusResult(
            source_label=normalize_label(source_label),
            target_label=normalize_label(target_label),
            path_count=path_count,
            inferred_type=inferred_type,
            upgraded=upgraded,
        )

    def contradiction_vote(
        self,
        source_label: str,
        positive_target: str,
        negative_target: str,
        *,
        max_hops: int = 7,
        max_paths: int = 64,
        weaken_factor: float = 0.9,
    ) -> ContradictionResult:
        positive_paths = self.find_paths(source_label, positive_target, max_hops=max_hops, max_paths=max_paths)
        negative_paths = self.find_paths(source_label, negative_target, max_hops=max_hops, max_paths=max_paths)
        pos_count = len(positive_paths)
        neg_count = len(negative_paths)
        total = pos_count + neg_count

        verdict: str
        confidence: float
        minority_edge_weakened = False

        if total == 0:
            verdict = "UNKNOWN"
            confidence = 0.0
        elif pos_count == neg_count:
            verdict = "TIE"
            confidence = 0.5
        elif pos_count > neg_count:
            verdict = normalize_label(positive_target)
            confidence = pos_count / total
            minority = self.get_edge(source_label, negative_target)
            if minority is not None:
                weakened = self.weaken_edge(minority.id, factor=weaken_factor)
                minority_edge_weakened = weakened is not None
        else:
            verdict = normalize_label(negative_target)
            confidence = neg_count / total
            minority = self.get_edge(source_label, positive_target)
            if minority is not None:
                weakened = self.weaken_edge(minority.id, factor=weaken_factor)
                minority_edge_weakened = weakened is not None

        return ContradictionResult(
            source_label=normalize_label(source_label),
            positive_target=normalize_label(positive_target),
            negative_target=normalize_label(negative_target),
            positive_paths=pos_count,
            negative_paths=neg_count,
            verdict=verdict,
            confidence=confidence,
            minority_edge_weakened=minority_edge_weakened,
        )

    def bootstrap(self, relations: Iterable[SeedRelation]) -> int:
        created = 0
        for source, target, edge_type, strength in relations:
            edge = self.create_edge(source, target, edge_type, strength=strength)
            if edge is not None:
                created += 1
        return created

    def bootstrap_default(self) -> int:
        seeds: list[SeedRelation] = [
            ("fire", "heat", EdgeType.IS_A, 0.92),
            ("heat", "burn", EdgeType.CAUSES, 0.90),
            ("steam", "heat", EdgeType.IS_A, 0.85),
            ("water", "cold", EdgeType.CORRELATES, 0.72),
            ("burn", "pain", EdgeType.CAUSES, 0.95),
            ("fire", "smoke", EdgeType.CORRELATES, 0.88),
        ]
        return self.bootstrap(seeds)

    def deduplicate_graph(self) -> dict[str, int]:
        """
        Deduplicate nodes with identical labels and edges between same source/target.
        Returns a summary of merged items.
        """
        nodes_merged = 0
        edges_merged = 0

        # 1. Deduplicate nodes
        # Use label normalization as the merging criterion
        label_to_node_id: dict[str, str] = {}
        all_node_ids = list(self.store.iter_node_ids())

        for node_id in all_node_ids:
            node = self.store.get_node(node_id)
            if node is None:
                continue

            norm_label = normalize_label(node.label)
            if norm_label in label_to_node_id:
                # Merge this node into the existing one
                surviving_id = label_to_node_id[norm_label]
                if surviving_id == node_id:
                    continue

                # Repoint incoming edges
                incoming = self.store.list_incoming(node_id)
                for edge in incoming:
                    # If an edge already exists from source to surviving_id, we'll merge it later
                    new_edge_id = make_edge_id(edge.source, surviving_id)
                    existing_new = self.store.get_edge(new_edge_id)
                    if existing_new:
                        # Update strength of existing if needed
                        new_strength = max(existing_new.strength, edge.strength)
                        self.store.update_edge_strength(new_edge_id, new_strength, increment_recall=False)
                        edges_merged += 1
                    else:
                        # Create new repointed edge
                        repointed = EdgeRecord(
                            id=new_edge_id,
                            source=edge.source,
                            target=surviving_id,
                            type=edge.type,
                            vector=edge.vector,
                            strength=edge.strength,
                            emotional_weight=edge.emotional_weight,
                            recall_count=edge.recall_count,
                            stability=edge.stability,
                            last_activated=edge.last_activated,
                            created=edge.created,
                        )
                        self.store.upsert_edge(repointed)
                    self.store.delete_edge(edge.id)

                # Repoint outgoing edges
                outgoing = self.store.list_outgoing(node_id)
                for edge in outgoing:
                    new_edge_id = make_edge_id(surviving_id, edge.target)
                    existing_new = self.store.get_edge(new_edge_id)
                    if existing_new:
                        new_strength = max(existing_new.strength, edge.strength)
                        self.store.update_edge_strength(new_edge_id, new_strength, increment_recall=False)
                        edges_merged += 1
                    else:
                        repointed = EdgeRecord(
                            id=new_edge_id,
                            source=surviving_id,
                            target=edge.target,
                            type=edge.type,
                            vector=edge.vector,
                            strength=edge.strength,
                            emotional_weight=edge.emotional_weight,
                            recall_count=edge.recall_count,
                            stability=edge.stability,
                            last_activated=edge.last_activated,
                            created=edge.created,
                        )
                        self.store.upsert_edge(repointed)
                    self.store.delete_edge(edge.id)

                # Delete the redundant node
                self.store.delete_node(node_id)
                nodes_merged += 1
            else:
                label_to_node_id[norm_label] = node_id

        # 2. Deduplicate edges (redundant if make_edge_id is stable, but good for consistency)
        # The repointing logic above already handles most cases by checking for existing edges.

        return {"nodes_merged": nodes_merged, "edges_merged": edges_merged}

    def close(self) -> None:
        self._persist_bloom()
        self.store.close()
