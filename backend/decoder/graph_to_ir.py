"""
decoder/graph_to_ir.py — Convert activated graph state back to SemanticIR.
"""
from __future__ import annotations

from typing import List, Dict, Any
from core.semantic_ir import SemanticIR, IRRelation
from graph.graph import CognitiveGraph


def convert_graph_to_ir(graph: CognitiveGraph, reasoning_result: Dict[str, Any]) -> SemanticIR:
    """
    Takes a reasoning result (with paths/chains) and converts it to a SemanticIR
    for final language generation.
    """
    # 1. Extract entities from the activated graph
    entities = [n.label for n in graph._nodes.values() if n.activation > 0.1]
    
    # 2. Extract relations from the activated graph
    relations = []
    for edge in graph._edges.values():
        if edge.weight > 0.1: # Significant edges only
            source_node = graph.get_node(edge.source)
            target_node = graph.get_node(edge.target)
            if source_node and target_node:
                relations.append(IRRelation(
                    source=source_node.label,
                    relation=edge.edge_type,
                    target=target_node.label,
                    confidence=edge.confidence
                ))
                
    # 3. Build SemanticIR
    ir = SemanticIR(
        text="", # To be generated
        entities=entities,
        relations=relations,
        intent="response",
        metadata={
            "reasoning_mode": reasoning_result.get("mode", "general"),
            "chains": reasoning_result.get("chains", [])
        }
    )
    
    return ir
