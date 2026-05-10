"""
core/cognitive_cycle.py — The background cognitive heartbeat.
"""
from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    from .kernel import CognitiveKernel

log = get_logger(__name__)


class CognitiveCycle:
    """
    Background heartbeat of the Paragi mind.
    
    Responsibilities:
    - Pulse spreading activation periodically.
    - Apply temporal decay.
    - Trigger maintenance tasks.
    """

    def __init__(self, kernel: CognitiveKernel, interval_ms: int = 200) -> None:
        self.kernel = kernel
        self.interval = interval_ms / 1000.0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background heartbeat."""
        if self._thread and self._thread.is_alive():
            return
            
        log.info(f"Starting cognitive cycle heartbeat ({self.interval * 1000}ms)")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the heartbeat."""
        log.info("Stopping cognitive cycle heartbeat...")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        """Main loop."""
        while not self._stop_event.is_set():
            t0 = time.perf_counter()
            
            try:
                self._pulse()
            except Exception as e:
                log.error(f"Error in cognitive cycle pulse: {e}")
                
            elapsed = time.perf_counter() - t0
            sleep_time = max(0, self.interval - elapsed)
            time.sleep(sleep_time)

    def _pulse(self) -> None:
        """A single cognitive pulse."""
        graph = self.kernel.graph
        
        # 1. Apply global temporal decay
        from graph.activation.decay import apply_global_decay
        apply_global_decay(graph)
        
        # 2. Spontaneous Spreading Activation
        # Find salient nodes and pulse them slightly
        from graph.activation.salience import get_salient_nodes
        salient = get_salient_nodes(graph, limit=5)
        
        for node_id, score in salient:
            # Pulse with a fraction of salience to keep concepts 'top of mind'
            graph.propagate_activation(node_id, energy=score * 0.1, decay=0.3)
            
        # 3. Deduplication (less frequent)
        if time.time() % 60 < 1: # roughly once a minute
             graph.deduplicate()
