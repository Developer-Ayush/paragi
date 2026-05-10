"""graph/memory/semantic.py — Semantic long-term memory."""
from __future__ import annotations
from graph.graph_store import GraphStore
from core.enums import EdgeType

class SemanticMemory:
    """
    Long-term factual and conceptual memory store.
    Provides semantic search over stabilized knowledge.
    """
    def __init__(self, store: GraphStore):
        self.store = store

    def retrieve_facts(self, concept_id: str) -> list[dict]:
        """Retrieves strong, stable facts connected to a concept."""
        facts = []
        outgoing = self.store.get_outgoing(concept_id)
        
        for edge in outgoing:
            # Only return stabilized knowledge
            if edge.strength > 0.4:
                target_node = self.store.get_node(edge.target)
                target_label = target_node.label if target_node else edge.target
                facts.append({
                    "relation": edge.type.value,
                    "target": target_label,
                    "confidence": edge._data.confidence,
                    "strength": edge.strength
                })
        
        return sorted(facts, key=lambda x: x["strength"], reverse=True)
