"""graph/memory/working.py — Working memory: active context for the current query."""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class WorkingMemoryEntry:
    key: str
    value: str
    created_at: float
    ttl_seconds: float = 300.0    # 5-minute default working memory


class WorkingMemory:
    """
    Short-term working memory for a single query context.
    Thread-safe, ephemeral — never persisted to disk.
    """
    def __init__(self, *, ttl_seconds: float = 300.0) -> None:
        self._entries: Dict[str, WorkingMemoryEntry] = {}
        self._lock = threading.RLock()
        self.default_ttl = ttl_seconds

    def set(self, key: str, value: str, *, ttl_seconds: Optional[float] = None) -> None:
        with self._lock:
            self._entries[key] = WorkingMemoryEntry(
                key=key, value=value, created_at=time.time(),
                ttl_seconds=ttl_seconds or self.default_ttl,
            )

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if time.time() - entry.created_at > entry.ttl_seconds:
                del self._entries[key]
                return None
            return entry.value

    def get_all(self) -> List[str]:
        with self._lock:
            now = time.time()
            return [
                e.value for e in self._entries.values()
                if now - e.created_at <= e.ttl_seconds
            ]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
