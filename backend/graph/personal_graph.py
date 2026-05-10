"""
graph/personal_graph.py — Private memory management.
"""
from __future__ import annotations

from typing import Dict, Optional
from .graph import CognitiveGraph
from .graph_store import InMemoryGraphStore


class PersonalGraphManager:
    """
    Manages isolated, per-user private memory graphs.
    """

    def __init__(self) -> None:
        self._graphs: Dict[str, CognitiveGraph] = {}

    def get_graph(self, user_id: str) -> CognitiveGraph:
        """Fetch or create a private graph for a user."""
        if user_id not in self._graphs:
            # Use an isolated In-Memory store for each user
            # In production, this would be a separate namespace in a graph DB
            store = InMemoryGraphStore()
            self._graphs[user_id] = CognitiveGraph(store)
        return self._graphs[user_id]

    def delete_graph(self, user_id: str) -> None:
        """Wipe a user's private memory."""
        if user_id in self._graphs:
            self._graphs[user_id].close()
            del self._graphs[user_id]
