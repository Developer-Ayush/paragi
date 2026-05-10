"""
graph/memory/working.py — Working Memory.

The transient 'scratchpad' of the system, holding active concepts 
and current reasoning context.
"""
from __future__ import annotations

from typing import Set, Dict, List
from ..graph import CognitiveGraph
from ..node import Node


class WorkingMemory:
    """
    Represents the active mental state.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph
        self._active_buffer: Set[str] = set()

    def add_to_context(self, node_id: str):
        """Add a node to the active working context."""
        self._active_buffer.add(node_id)
        node = self.graph.get_node(node_id)
        if node:
            node.set_activation(1.0) # Full activation when added to WM

    def clear_context(self):
        self._active_buffer.clear()

    def get_active_nodes(self) -> List[Node]:
        """Return all nodes currently in working memory."""
        nodes = []
        for nid in self._active_buffer:
            node = self.graph.get_node(nid)
            if node:
                nodes.append(node)
        return nodes

    def get_context_summary(self) -> Dict[str, float]:
        """Summary of active concepts and their activation levels."""
        return {nid: self.graph.get_node(nid).activation 
                for nid in self._active_buffer if self.graph.get_node(nid)}
