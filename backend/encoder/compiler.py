"""
encoder/compiler.py — The Semantic Compiler entry point.

Text → SemanticIR → Graph Build.
"""
from __future__ import annotations

from typing import Optional
from core.semantic_ir import SemanticIR
from graph.graph import CognitiveGraph
from graph.graph_builder import GraphBuilder
from .semantic_encoder import SemanticEncoder


class SemanticCompiler:
    """
    Top-level entry point for the Paragi encoder pipeline.
    """

    def __init__(self, graph: Optional[CognitiveGraph] = None) -> None:
        self.encoder = SemanticEncoder()
        self.graph = graph
        self.builder = GraphBuilder(graph) if graph else None

    def compile(self, text: str, update_graph: bool = True) -> SemanticIR:
        """
        Convert text to SemanticIR and optionally update the graph.
        """
        # 1. Understanding: Text -> SemanticIR
        ir = self.encoder.encode(text)
        
        # 2. Structure: SemanticIR -> Graph
        if update_graph and self.builder:
            self.builder.compile(ir)
            
        return ir