"""Phase 2 + Phase 4 — Temporary Memory Store.

Provides TTL-based temporary context for realtime knowledge and episodic memory.
Realtime knowledge (news, weather, stocks) is NEVER permanently stored in the graph.
Episodic memory decays over time with configurable half-life.

This module enforces the core principle:
  realtime knowledge → temporary context only
  episodic memory → weighted storage with decay
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List


class MemoryType(str, Enum):
    REALTIME = "realtime"
    EPISODIC = "episodic"


@dataclass(slots=True)
class TemporaryEntry:
    key: str
    value: str
    source: str
    memory_type: MemoryType
    created_at: float
    ttl_seconds: float
    weight: float  # 1.0 = full strength, decays toward 0
    access_count: int


class TemporaryMemoryStore:
    """TTL-based temporary memory. Thread-safe. Never persisted to disk.

    Two modes:
    - REALTIME: hard TTL expiry, no graph storage ever
    - EPISODIC: soft decay (weight decreases), eventually pruned
    """

    def __init__(
        self,
        *,
        default_realtime_ttl: float = 3600.0,
        episodic_decay_hours: float = 24.0,
    ) -> None:
        self._lock = threading.RLock()
        self._entries: Dict[str, TemporaryEntry] = {}
        self.default_realtime_ttl = default_realtime_ttl
        self.episodic_decay_hours = episodic_decay_hours

    def store_realtime(
        self,
        key: str,
        value: str,
        source: str = "web",
        ttl_seconds: float | None = None,
    ) -> TemporaryEntry:
        """Store realtime information with hard TTL expiry."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_realtime_ttl
        entry = TemporaryEntry(
            key=key,
            value=value,
            source=source,
            memory_type=MemoryType.REALTIME,
            created_at=time.time(),
            ttl_seconds=ttl,
            weight=1.0,
            access_count=0,
        )
        with self._lock:
            self._entries[key] = entry
        return entry

    def store_episodic(
        self,
        key: str,
        value: str,
        source: str = "conversation",
        initial_weight: float = 1.0,
    ) -> TemporaryEntry:
        """Store episodic memory with decay-based weight."""
        # Episodic entries have a long TTL but their weight decays
        ttl = self.episodic_decay_hours * 3600.0 * 3  # 3x half-life before prune
        entry = TemporaryEntry(
            key=key,
            value=value,
            source=source,
            memory_type=MemoryType.EPISODIC,
            created_at=time.time(),
            ttl_seconds=ttl,
            weight=initial_weight,
            access_count=0,
        )
        with self._lock:
            self._entries[key] = entry
        return entry

    def get(self, key: str) -> TemporaryEntry | None:
        """Retrieve a temporary entry, returning None if expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if self._is_expired(entry):
                del self._entries[key]
                return None
            # Apply episodic decay
            if entry.memory_type == MemoryType.EPISODIC:
                entry.weight = self._compute_episodic_weight(entry)
            entry.access_count += 1
            return entry

    def get_context(self, query_text: str) -> List[TemporaryEntry]:
        """Find all non-expired temporary entries relevant to a query."""
        self._purge_expired()
        query_lower = query_text.strip().lower()
        query_tokens = set(query_lower.split())
        results: list[TemporaryEntry] = []
        with self._lock:
            for entry in self._entries.values():
                key_tokens = set(entry.key.lower().split())
                if key_tokens & query_tokens:
                    if entry.memory_type == MemoryType.EPISODIC:
                        entry.weight = self._compute_episodic_weight(entry)
                    results.append(entry)
        results.sort(key=lambda e: (-e.weight, -e.created_at))
        return results[:10]

    def is_realtime_cached(self, key: str) -> bool:
        """Check if we already have a non-expired realtime answer."""
        entry = self.get(key)
        return entry is not None and entry.memory_type == MemoryType.REALTIME

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    def _is_expired(self, entry: TemporaryEntry) -> bool:
        return (time.time() - entry.created_at) > entry.ttl_seconds

    def _compute_episodic_weight(self, entry: TemporaryEntry) -> float:
        """Exponential decay: weight = initial * 2^(-age_hours / half_life_hours)."""
        age_hours = (time.time() - entry.created_at) / 3600.0
        if self.episodic_decay_hours <= 0:
            return entry.weight
        decay_factor = 0.5 ** (age_hours / self.episodic_decay_hours)
        return max(0.01, entry.weight * decay_factor)

    def _purge_expired(self) -> int:
        """Remove all expired entries. Returns count of purged entries."""
        now = time.time()
        purged = 0
        with self._lock:
            expired_keys = [
                key for key, entry in self._entries.items()
                if (now - entry.created_at) > entry.ttl_seconds
            ]
            for key in expired_keys:
                del self._entries[key]
                purged += 1
        return purged
