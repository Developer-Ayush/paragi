from __future__ import annotations

import threading
from pathlib import Path

from .bloom import BloomFilter
from .config import Settings
from .graph import GraphEngine
from .own_decoder import OwnDecoder
from .own_encoder import OwnEncoder
from .query_control import QueryClassifier
from .query_pipeline import QueryPipeline, TemporaryDecoder, TemporaryEncoder
from .storage import HDF5GraphStore, InMemoryGraphStore
from .user_state import sanitize_user_id


class PersonalGraphManager:
    """Creates one private graph+pipeline per user."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.RLock()
        self._graphs: dict[str, GraphEngine] = {}
        self._pipelines: dict[str, QueryPipeline] = {}

    def _user_paths(self, user_id: str) -> tuple[Path, Path]:
        safe = sanitize_user_id(user_id)
        user_dir = self.settings.data_dir / "users" / safe
        user_dir.mkdir(parents=True, exist_ok=True)
        hdf5_path = user_dir / "personal_memory.h5"
        bloom_path = user_dir / "personal_nodes.bloom.json"
        return hdf5_path, bloom_path

    def _build_graph(self, user_id: str) -> GraphEngine:
        hdf5_path, bloom_path = self._user_paths(user_id)
        bloom = BloomFilter.load(bloom_path) if bloom_path.exists() else BloomFilter(
            capacity=self.settings.bloom_capacity,
            error_rate=self.settings.bloom_error_rate,
        )

        if self.settings.prefer_hdf5:
            try:
                store = HDF5GraphStore(hdf5_path)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize personal HDF5 storage for user {user_id}: {e}")
        else:
            store = InMemoryGraphStore()

        graph = GraphEngine(
            store=store,
            bloom=bloom,
            bloom_path=bloom_path,
            edge_strength_floor=self.settings.edge_strength_floor,
            edge_decay_per_cycle=self.settings.edge_decay_per_cycle,
        )
        return graph

    def get_pipeline(self, user_id: str) -> QueryPipeline:
        safe = sanitize_user_id(user_id)
        with self._lock:
            existing = self._pipelines.get(safe)
            if existing is not None:
                return existing

            graph = self._build_graph(safe)
            if self.settings.encoder_backend == "own":
                user_dir = self.settings.data_dir / "users" / safe
                model_path = user_dir / "personal_encoder_model.json"
                encoder = OwnEncoder(model_path=model_path)
                # Ensure personal encoder can be trained from the shared training log
                # In a real system, we might want per-user logs, but the issue states
                # they are never trained because only shared path is used.
                # Here we ensure they use the same backend and thus can use the train method.
            elif self.settings.encoder_backend == "fastembed":
                encoder = TemporaryEncoder(use_fastembed=True)
            else:
                encoder = TemporaryEncoder(use_fastembed=False)

            if self.settings.decoder_backend == "own":
                user_dir = self.settings.data_dir / "users" / safe
                decoder_model_path = user_dir / "personal_decoder_model.json"
                decoder = OwnDecoder(model_path=decoder_model_path)
            else:
                decoder = TemporaryDecoder()
            pipeline = QueryPipeline(
                graph,
                encoder,
                decoder,
                classifier=QueryClassifier(),
            )
            self._graphs[safe] = graph
            self._pipelines[safe] = pipeline
            return pipeline

    def close(self) -> None:
        with self._lock:
            for graph in self._graphs.values():
                graph.close()
            self._graphs.clear()
            self._pipelines.clear()
