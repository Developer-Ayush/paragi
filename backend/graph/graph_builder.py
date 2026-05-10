"""graph/graph_builder.py — GraphBuilder: insert SemanticIR into the cognitive graph."""
from __future__ import annotations

from typing import List, Tuple

from core.semantic_ir import SemanticIR, Relation
from core.enums import EdgeType
from core.constants import VECTOR_SIZE
from core.logger import get_logger
from graph.graph import GraphEngine

log = get_logger(__name__)


class GraphBuilder:
    """
    Bridges the encoder and the graph.

    Takes a SemanticIR produced by the SemanticCompiler and:
    1. Ensures all entities exist as graph nodes.
    2. Inserts all extracted relations as typed edges.
    3. Inserts LLM-extracted graph_edges.

    The GraphBuilder does NOT reason — it only structures.
    """

    def __init__(self, graph: GraphEngine, *, default_strength: float = 0.3) -> None:
        self.graph = graph
        self.default_strength = default_strength

    def insert(self, ir: SemanticIR, *, allow_learning: bool = True) -> Tuple[int, int]:
        """
        Insert SemanticIR into the graph.

        Returns:
            (nodes_created, edges_created) counts.
        """
        if not allow_learning or ir.learnability <= 0.0:
            return 0, 0

        nodes_before = self.graph.count_nodes()
        edges_created = 0

        # 1. Ensure all entities exist as nodes
        for entity in ir.entities:
            if entity:
                self.graph.create_or_get_node(entity)

        # 2. Insert extracted text relations
        for relation in ir.relations:
            if relation.source and relation.target:
                edge_type = self._parse_edge_type(relation.relation)
                strength = min(1.0, self.default_strength * relation.confidence)
                vec = self._build_vector(ir.semantic_vector, edge_type)
                self.graph.create_edge(
                    relation.source, relation.target, edge_type,
                    strength=strength, vector=vec,
                    confidence=relation.confidence,
                )
                edges_created += 1

        # 3. Insert LLM-extracted graph_edges (higher confidence)
        for edge_dict in ir.graph_edges:
            src = str(edge_dict.get("source", "")).strip()
            tgt = str(edge_dict.get("target", "")).strip()
            rel = str(edge_dict.get("relation", "CORRELATES")).strip().upper()
            if src and tgt:
                edge_type = self._parse_edge_type(rel)
                vec = self._build_vector(ir.semantic_vector, edge_type)
                self.graph.create_edge(
                    src, tgt, edge_type,
                    strength=self.default_strength,
                    vector=vec, confidence=0.7,
                )
                edges_created += 1

        # 4. Personal fact: store self → "attribute value" edge
        if ir.intent == "personal_fact" and ir.personal_attribute and ir.personal_value:
            memory_label = f"{ir.personal_attribute} {ir.personal_value}"
            self.graph.create_edge(
                "self", memory_label, EdgeType.CORRELATES,
                strength=0.95,
                vector=self._build_vector(ir.semantic_vector, EdgeType.CORRELATES),
                confidence=0.99,
            )
            edges_created += 1

        nodes_created = max(0, self.graph.count_nodes() - nodes_before)
        log.debug(f"GraphBuilder: +{nodes_created} nodes, +{edges_created} edges")
        return nodes_created, edges_created

    @staticmethod
    def _parse_edge_type(rel: str) -> EdgeType:
        """Parse a relation string to EdgeType, defaulting to CORRELATES."""
        try:
            return EdgeType(rel.upper())
        except ValueError:
            return EdgeType.CORRELATES

    @staticmethod
    def _build_vector(semantic_vector: List[float], edge_type: EdgeType) -> List[float]:
        """Build a 1024-dim edge vector from the semantic vector."""
        vec = [0.0] * VECTOR_SIZE
        # Map 700-dim semantic vector into positions 0-699
        for i, v in enumerate(semantic_vector[:700]):
            vec[i] = v
        # Set edge-type discriminant dimension
        type_dims = {
            EdgeType.CAUSES: 850,
            EdgeType.IS_A: 860,
            EdgeType.TEMPORAL: 870,
            EdgeType.ANALOGY: 880,
            EdgeType.CONTRADICTS: 890,
            EdgeType.CORRELATES: 900,
        }
        dim = type_dims.get(edge_type, 910)
        if dim < VECTOR_SIZE:
            vec[dim] = 1.0
        return vec


def insert_ir(graph: GraphEngine, ir: SemanticIR, *, allow_learning: bool = True) -> Tuple[int, int]:
    """Convenience function for inserting a SemanticIR into the graph."""
    return GraphBuilder(graph).insert(ir, allow_learning=allow_learning)