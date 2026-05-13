"""
core/kernel.py — The Paragi Resource Kernel.
"""
from __future__ import annotations

from typing import Optional
from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore, GraphStore
from graph.persistence.hdf5_store import HDF5GraphStore
from .cognitive_cycle import CognitiveCycle
from graph.expansion_worker import ExpansionWorker
from graph.persistence.bloom import BloomFilter
from .user_state import UserStateManager
from graph.personal_graph import PersonalGraphManager
from .config import Settings
from utils.llm_refiner import LLMRefiner


class CognitiveKernel:
    """
    Maintains core system resources and provides them to orchestrators.
    """

    def __init__(self, store: Optional[GraphStore] = None) -> None:
        settings = Settings.from_env()

        if store:
            self.store = store
        elif settings.prefer_hdf5:
            try:
                self.store = HDF5GraphStore(settings.hdf5_path)
            except Exception as e:
                # Architectural violation to fallback silently if HDF5 is preferred
                raise RuntimeError(f"Failed to initialize HDF5GraphStore at {settings.hdf5_path}: {e}")
        else:
            self.store = InMemoryGraphStore()

        self.graph = CognitiveGraph(self.store)
        
        settings = Settings.from_env()

        # OS Layer Components
        self.bloom = BloomFilter(
            capacity=settings.bloom_capacity,
            error_rate=settings.bloom_error_rate
        )
        self.user_state = UserStateManager()
        self.personal_graphs = PersonalGraphManager()
        
        # LLM Interface (for semantic reconstruction)
        self.llm = LLMRefiner(
            backend=settings.llm_backend,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens
        )
        
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
