from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

from utils.external_sources import ExternalKnowledgeConnector, RelationCandidate
from .graph import GraphEngine
from models.models import normalize_label


@dataclass(slots=True)
class ExpansionNode:
    id: str
    query_text: str
    source: str
    target: str
    status: str  # pending | resolved | failed
    created_at: float
    updated_at: float
    attempts: int
    resolved_edges: int
    last_error: str
    provenance: str


class ExpansionQueueStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._nodes: dict[str, ExpansionNode] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            payload = []
        if not isinstance(payload, list):
            payload = []
        for item in payload:
            try:
                node = ExpansionNode(
                    id=str(item["id"]),
                    query_text=str(item["query_text"]),
                    source=str(item["source"]),
                    target=str(item["target"]),
                    status=str(item["status"]),
                    created_at=float(item["created_at"]),
                    updated_at=float(item["updated_at"]),
                    attempts=int(item["attempts"]),
                    resolved_edges=int(item["resolved_edges"]),
                    last_error=str(item.get("last_error", "")),
                    provenance=str(item.get("provenance", "")),
                )
                self._nodes[node.id] = node
            except Exception:
                continue

    def _save(self) -> None:
        data = [asdict(node) for node in sorted(self._nodes.values(), key=lambda x: x.created_at)]
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def enqueue(self, query_text: str, source: str, target: str) -> ExpansionNode:
        source = normalize_label(source)
        target = normalize_label(target)
        query_text = query_text.strip()
        with self._lock:
            for node in self._nodes.values():
                if node.source == source and node.target == target and node.status in {"pending", "resolved"}:
                    return node

            ts = time.time()
            node = ExpansionNode(
                id=uuid.uuid4().hex,
                query_text=query_text,
                source=source,
                target=target,
                status="pending",
                created_at=ts,
                updated_at=ts,
                attempts=0,
                resolved_edges=0,
                last_error="",
                provenance="",
            )
            self._nodes[node.id] = node
            self._save()
            return node

    def get_pending(self, limit: int = 10) -> List[ExpansionNode]:
        with self._lock:
            items = [node for node in self._nodes.values() if node.status == "pending"]
            items.sort(key=lambda n: (n.attempts, n.created_at))
            return items[:limit]

    def mark_resolved(self, node_id: str, created_edges: int, provenance: str) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return
            node.status = "resolved"
            node.updated_at = time.time()
            node.resolved_edges = created_edges
            node.provenance = provenance
            node.last_error = ""
            self._save()

    def mark_attempt(self, node_id: str, error: str) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return
            node.attempts += 1
            node.updated_at = time.time()
            node.last_error = error
            self._save()

    def mark_failed(self, node_id: str, error: str) -> None:
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return
            node.status = "failed"
            node.updated_at = time.time()
            node.last_error = error
            self._save()

    def list_recent(self, limit: int = 20) -> List[ExpansionNode]:
        with self._lock:
            items = sorted(self._nodes.values(), key=lambda n: n.created_at, reverse=True)
            return items[:limit]


class ExpansionResolver:
    def __init__(
        self,
        graph: GraphEngine,
        queue: ExpansionQueueStore,
        connectors: List[ExternalKnowledgeConnector],
        *,
        max_attempts: int = 5,
    ) -> None:
        self.graph = graph
        self.queue = queue
        self.connectors = connectors
        self.max_attempts = max_attempts

    def resolve(self, node_id: str) -> int:
        with self.queue._lock:
            node = self.queue._nodes.get(node_id)
        if node:
            return self._resolve_one(node)
        return 0

    def resolve_pending(self, max_items: int = 3) -> int:
        resolved_count = 0
        pending = self.queue.get_pending(limit=max_items)
        for node in pending:
            created = self._resolve_one(node)
            if created > 0:
                resolved_count += 1
        return resolved_count

    def resolve_relation(self, source: str, target: str, *, timeout_seconds: float = 0.8) -> tuple[int, str]:
        source = normalize_label(source)
        target = normalize_label(target)
        for connector in self.connectors:
            candidates = connector.fetch_relation(source, target, timeout_seconds=timeout_seconds)
            if not candidates:
                continue
            created = self._ingest_candidates(candidates)
            if created > 0:
                return created, connector.name
        return 0, ""

    def resolve_concept(self, concept: str, *, timeout_seconds: float = 0.8) -> tuple[int, str]:
        concept = normalize_label(concept)
        for connector in self.connectors:
            candidates = connector.fetch_concept(concept, timeout_seconds=timeout_seconds)
            if not candidates:
                continue
            created = self._ingest_candidates(candidates)
            if created > 0:
                return created, connector.name
        return 0, ""

    def _resolve_one(self, node: ExpansionNode) -> int:
        for connector in self.connectors:
            if node.target:
                candidates = connector.fetch_relation(node.source, node.target)
            else:
                candidates = connector.fetch_concept(node.source)
            
            if candidates:
                created = self._ingest_candidates(candidates)
                if created > 0:
                    self.queue.mark_resolved(node.id, created_edges=created, provenance=connector.name)
                    return created

        self.queue.mark_attempt(node.id, error="no external evidence")
        refreshed = self.queue.get_pending(limit=1000)
        attempts = next((n.attempts for n in refreshed if n.id == node.id), node.attempts + 1)
        if attempts >= self.max_attempts:
            self.queue.mark_failed(node.id, error="max attempts reached without evidence")
        return 0

    def _ingest_candidates(self, candidates: List[RelationCandidate]) -> int:
        seen: set[tuple[str, str, str]] = set()
        created = 0
        for candidate in candidates:
            key = (candidate.source, candidate.target, candidate.edge_type.value)
            if key in seen:
                continue
            seen.add(key)
            self.graph.create_edge(
                source_label=candidate.source,
                target_label=candidate.target,
                edge_type=candidate.edge_type,
                strength=candidate.strength,
            )
            created += 1
        return created
