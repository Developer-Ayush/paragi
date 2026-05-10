from __future__ import annotations

import threading
from typing import Optional

from .expansion import ExpansionResolver


class ExpansionWorker:
    """Background expansion-node resolver."""

    def __init__(self, resolver: ExpansionResolver, interval_seconds: float) -> None:
        self.resolver = resolver
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_resolved = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="paragi-expansion-worker")
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.last_resolved = self.resolver.resolve_pending(max_items=5)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

