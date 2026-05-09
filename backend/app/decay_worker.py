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
        # Every N cycles, we also run semantic deduplication
        dedup_cycle_interval = 10
        cycle_count = 0

        # Lazy load encoder to avoid memory overhead if not needed immediately
        encoder = None

        while not self._stop_event.wait(self.interval_seconds):
            self.last_decayed_edges = self.graph.decay_all_edges()
            cycle_count += 1
            if cycle_count >= dedup_cycle_interval:
                if encoder is None:
                    from .own_encoder import OwnEncoder
                    encoder = OwnEncoder()

                self.graph.deduplicate_graph(encoder=encoder)
                self.graph.prune_edges()
                cycle_count = 0

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

