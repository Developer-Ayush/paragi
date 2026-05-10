"""
graph/graph_builder.py — The Semantic Compiler.

Translates high-level SemanticIR into low-level graph topology.
This is where meaning becomes structure.
"""
from __future__ import annotations

import hashlib
from typing import List, Optional
from core.semantic_ir import SemanticIR, IRRelation
from core.enums import EdgeType, NodeType
from .graph import CognitiveGraph
from .node import Node
from .edge import Edge


class GraphBuilder:
    """
    Compiler that transforms SemanticIR into graph mutations.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph

    def compile(self, ir: SemanticIR) -> None:
        """Process a SemanticIR and update the graph."""
        
        # 1. Process entities and concepts as nodes
        for entity in ir.entities:
            self._ensure_node(entity, NodeType.ENTITY)
        
        for concept in ir.concepts:
            self._ensure_node(concept, NodeType.CONCEPT)
            
        # 2. Process relations as edges
        for rel in ir.relations:
            self._add_semantic_relation(rel)
            
        # 3. Process temporal markers
        # (Implementation placeholder for temporal state updates)
        
        # 4. Process causal markers
        # (Implementation placeholder for causal strengthening)

    def _ensure_node(self, label: str, node_type: NodeType) -> str:
        """Ensure a node exists for a given label, creating it if necessary."""
        node_id = self._generate_id(label)
        existing = self.graph.get_node(node_id)
        
        if not existing:
            new_node = Node(
                id=node_id,
                label=label,
                type=node_type, 
                confidence=1.0
            )
            self.graph.add_node(new_node)
            
        return node_id

    def create_or_reinforce_edge(
        self, 
        source_label: str, 
        target_label: str, 
        edge_type: EdgeType,
        weight: float = 0.2,
        confidence: float = 1.0
    ) -> None:
        """Helper for manual or autonomous edge creation."""
        from core.semantic_ir import IRRelation
        rel = IRRelation(
            source=source_label,
            target=target_label,
            relation=edge_type,
            confidence=confidence
        )
        self._add_semantic_relation(rel)

    def _add_semantic_relation(self, rel: IRRelation) -> None:
        """Add or reinforce a directed edge between concepts."""
        source_id = self._ensure_node(rel.source, NodeType.CONCEPT)
        target_id = self._ensure_node(rel.target, NodeType.CONCEPT)
        
        existing_edge = self.graph.get_edge(source_id, target_id)
        
        if existing_edge:
            # Reinforce if it's the same type
            if existing_edge.edge_type == rel.relation:
                existing_edge.reinforce()
                self.graph.add_edge(existing_edge) # Update store
        else:
            # Create new edge
            new_edge = Edge(
                source=source_id,
                target=target_id,
                edge_type=rel.relation,
                weight=0.2, # Initial weight
                confidence=rel.confidence,
                metadata=rel.attributes
            )
            self.graph.add_edge(new_edge)

    def _generate_id(self, label: str) -> str:
        """Generate a deterministic ID for a label."""
        return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]