"""
graph/expansion_worker.py — Autonomous knowledge acquisition.
"""
from __future__ import annotations

import time
import threading
import queue
from typing import TYPE_CHECKING, List, Dict, Any
from core.logger import get_logger
from core.enums import EdgeType
from .edge import Edge
from utils.realtime_lookup import fetch_realtime_answer

if TYPE_CHECKING:
    from core.kernel import CognitiveKernel

log = get_logger(__name__)


class ExpansionWorker:
    """
    Background worker that resolves unknown concepts and fetches external knowledge.
    """

    def __init__(self, kernel: CognitiveKernel) -> None:
        self.kernel = kernel
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def enqueue(self, node_label: str) -> None:
        """Add a concept to the expansion queue."""
        self._queue.put(node_label)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                # Wait with timeout to check stop event
                label = self._queue.get(timeout=1.0)
                self._resolve(label)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                log.error(f"Error in expansion worker: {e}")

    def _resolve(self, label: str) -> None:
        """Resolve a concept using external sources (Wikipedia + LLM Digest)."""
        log.info(f"Expanding knowledge for: {label}")
        
        # 1. Fetch real-time data from Wikipedia
        web_res = fetch_realtime_answer(f"What is {label}?")
        if not web_res:
            log.info(f"No web results for: {label}")
            return
            
        summary, source = web_res
        log.info(f"Found web knowledge for '{label}' from {source}")
        
        # 2. Use LLM to digest summary into graph edges
        if self.kernel.llm:
            edges = self.kernel.llm.digest_into_graph(summary)
            for edge in edges:
                self._add_external_fact(
                    edge["source"], 
                    edge["target"], 
                    EdgeType.get(edge["relation"], EdgeType.ASSOCIATED_WITH)
                )
        else:
            # Fallback if no LLM (Simple heuristic)
            self._add_external_fact(label, "concept", EdgeType.IS_A)

    def _add_external_fact(self, source_label: str, target_label: str, edge_type: EdgeType) -> None:
        from graph.graph_builder import GraphBuilder
        builder = GraphBuilder(self.kernel.graph)
        
        # Use builder to handle node creation/ID generation
        builder.create_or_reinforce_edge(
            source_label=source_label,
            target_label=target_label,
            edge_type=edge_type,
            weight=0.6,
            confidence=0.8
        )
        log.info(f"Learned external fact: {source_label} --{edge_type}--> {target_label}")
