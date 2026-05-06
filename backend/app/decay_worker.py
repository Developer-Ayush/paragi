from __future__ import annotations

import threading
from typing import Optional

from .graph import GraphEngine


class DecayWorker:
    """Background decay loop for edge strength."""

    def __init__(self, graph: GraphEngine, interval_seconds: float) -> None:
        self.graph = graph
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_decayed_edges = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="paragi-decay-worker")
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            self.last_decayed_edges = self.graph.decay_all_edges()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

