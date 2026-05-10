"""graph/memory/episodic.py — Episodic memory with time-decay.

Ported from app/temporary_memory.py (EPISODIC mode).
"""
from __future__ import annotations
import math
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(slots=True)
class EpisodicEntry:
    key: str
    value: str
    source: str
    created_at: float
    weight: float          # decays over time
    access_count: int


class EpisodicMemory:
    """
    Episodic memory: personal experiences and conversation facts.
    Weight decays exponentially with time.
    """
    def __init__(self, *, decay_hours: float = 24.0) -> None:
        self._entries: Dict[str, EpisodicEntry] = {}
        self._lock = threading.RLock()
        self.decay_hours = decay_hours

    def store(self, key: str, value: str, source: str = "conversation", *, initial_weight: float = 1.0) -> EpisodicEntry:
        entry = EpisodicEntry(
            key=key, value=value, source=source,
            created_at=time.time(), weight=initial_weight, access_count=0,
        )
        with self._lock:
            self._entries[key] = entry
        return entry

    def get(self, key: str) -> Optional[EpisodicEntry]:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            entry.weight = self._decay(entry)
            entry.access_count += 1
            if entry.weight < 0.01:
                del self._entries[key]
                return None
            return entry

    def search(self, query: str) -> List[EpisodicEntry]:
        query_tokens = set(query.lower().split())
        results = []
        with self._lock:
            for entry in list(self._entries.values()):
                entry.weight = self._decay(entry)
                if set(entry.key.lower().split()) & query_tokens:
                    results.append(entry)
        results.sort(key=lambda e: (-e.weight, -e.created_at))
        return results[:10]

    def _decay(self, entry: EpisodicEntry) -> float:
        age_hours = (time.time() - entry.created_at) / 3600.0
        if self.decay_hours <= 0:
            return entry.weight
        return max(0.0, entry.weight * (0.5 ** (age_hours / self.decay_hours)))

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
