"""cognition/orchestration.py — Central cognition pipeline orchestrator."""
from __future__ import annotations

class Orchestrator:
    """Top-level pipeline coordinator tying Introspection, Memory, and Reasoning."""
    def __init__(self, compiler, graph_builder, reasoner, decoder):
        self.compiler = compiler
        self.graph_builder = graph_builder
        self.reasoner = reasoner
        self.decoder = decoder
        
    def process(self, text: str, context: dict = None) -> str:
        # 1. Compile
        ir = self.compiler.compile(text)
        
        # 2. Build / Update Graph
        if ir.learnability > 0.5:
            self.graph_builder.insert(ir)
            
        # 3. Reason
        result = self.reasoner.reason(ir)
        
        # 4. Decode
        return self.decoder.generate(
            question=text,
            graph_answer=result.answer,
            node_path=result.node_path,
            edge_types=[],
            confidence=result.confidence
        )
