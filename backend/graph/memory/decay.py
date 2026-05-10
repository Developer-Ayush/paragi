"""graph/memory/decay.py — Edge decay worker for the cognitive graph."""
from __future__ import annotations
import threading
import time
from core.logger import get_logger

log = get_logger(__name__)


class DecayWorker:
    """
    Background thread that periodically decays all graph edges.
    Ported from app/graph.py DecayWorker.
    """
    def __init__(self, graph: object, interval_seconds: float = 30.0) -> None:
        self._graph = graph
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="DecayWorker")
        self._thread.start()
        log.info(f"DecayWorker started (interval={self._interval}s)")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def _run(self) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            try:
                count = self._graph.decay_all_edges()  # type: ignore
                pruned = self._graph.prune_edges()     # type: ignore
                log.debug(f"DecayWorker: decayed {count} edges, pruned {pruned}")
            except Exception as exc:
                log.warning(f"DecayWorker error: {exc}")
