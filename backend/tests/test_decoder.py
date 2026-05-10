"""
tests/test_decoder.py — Verification for Phase 5.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from graph.node import Node
from graph.edge import Edge
from core.enums import EdgeType
from decoder.graph_to_ir import convert_graph_to_ir
from decoder.semantic_reconstruction import SemanticReconstructor
from decoder.explanation_builder import ExplanationBuilder
from decoder.language_generator import LanguageGenerator


def test_full_reconstruction():
    print("\n[TEST] Full Decoder Pipeline")
    
    # 1. Setup Mock Activated Graph: Fire -> burns -> injury
    store = InMemoryGraphStore()
    graph = CognitiveGraph(store)
    
    n1 = Node(id="1", label="Fire", activation=1.0)
    n2 = Node(id="2", label="burns", activation=0.8)
    n3 = Node(id="3", label="injury", activation=0.6)
    
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    
    graph.add_edge(Edge(source="1", target="2", edge_type=EdgeType.CAUSES, weight=0.8))
    graph.add_edge(Edge(source="2", target="3", edge_type=EdgeType.CAUSES, weight=0.7))
    
    # 2. Mock Reasoning Result
    reasoning_res = {
        "mode": "causal",
        "chains": ["Fire -> burns -> injury"]
    }
    
    # 3. Graph -> IR
    ir = convert_graph_to_ir(graph, reasoning_res)
    print(f"Generated IR Relations: {len(ir.relations)}")
    
    # 4. IR -> Meaning
    reconstructor = SemanticReconstructor()
    meaning = reconstructor.reconstruct(ir)
    print(f"Meaning Representation: {meaning}")
    
    # 5. Meaning -> Text
    generator = LanguageGenerator() # No LLM for test
    text = generator.generate(meaning)
    print(f"Generated Text: {text}")
    
    assert "Fire" in text
    assert "burns" in text
    assert "injury" in text
    
    print("Test Passed!")


if __name__ == "__main__":
    try:
        test_full_reconstruction()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
