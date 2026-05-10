"""graph/memory/semantic.py — Semantic long-term memory."""
from __future__ import annotations
from graph.graph_store import GraphStore

class SemanticMemory:
    """
    Long-term factual and conceptual memory store.
    Provides semantic search over stabilized knowledge.
    """
    def __init__(self, store: GraphStore):
        self.store = store

    def retrieve_facts(self, concept: str) -> list:
        return []
