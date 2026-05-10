"""
core/kernel.py — The Paragi Resource Kernel.
"""
from __future__ import annotations

from typing import Optional
from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore, GraphStore
from .cognitive_cycle import CognitiveCycle
from graph.expansion_worker import ExpansionWorker
from graph.persistence.bloom import BloomFilter
from .user_state import UserStateManager
from graph.personal_graph import PersonalGraphManager


class CognitiveKernel:
    """
    Maintains core system resources and provides them to orchestrators.
    """

    def __init__(self, store: Optional[GraphStore] = None) -> None:
        self.store = store or InMemoryGraphStore()
        self.graph = CognitiveGraph(self.store)
        
        # OS Layer Components
        self.bloom = BloomFilter()
        self.user_state = UserStateManager()
        self.personal_graphs = PersonalGraphManager()
        
        # Background Systems
        self.cycle = CognitiveCycle(self)
        self.expansion = ExpansionWorker(self)

    def startup(self) -> None:
        """Boot all background cognitive processes."""
        self.cycle.start()
        self.expansion.start()

    def shutdown(self) -> None:
        """Gracefully stop all background processes."""
        self.cycle.stop()
        self.expansion.stop()
        self.store.close()
