"""
tests/test_high_fidelity.py — Verification for Phase 9.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from graph.edge import Edge
from core.enums import EdgeType
from core.constants import VECTOR_SIZE, RANGE_EMOTIONAL_RANGE, RANGE_FACTUAL_WORLD


def test_hebbian_formula():
    print("\n[TEST] High-Fidelity Hebbian Formula")
    
    # η=0.1, α=0.01, β=0.005 (defaults)
    # Δstrength = η(S - weight) + αR - βD
    
    edge = Edge(
        source="A", target="B", 
        edge_type=EdgeType.CAUSES, 
        weight=0.5,
        decay_param=0.1
    )
    
    # 1. First reinforcement
    # R=1, S=0.8
    # Δ = 0.1 * (0.8 - 0.5) + 0.01 * 1 - 0.005 * 0.1
    # Δ = 0.1 * 0.3 + 0.01 - 0.0005 = 0.03 + 0.01 - 0.0005 = 0.0395
    # next_weight = 0.5395
    
    edge.reinforce(s_score=0.8)
    print(f"Weight after reinforcement: {edge.weight:.4f}")
    assert abs(edge.weight - 0.5395) < 0.0001
    
    print("Hebbian Formula Test Passed!")


def test_vector_decay():
    print("\n[TEST] Per-Dimension Vector Decay")
    
    vector = [1.0] * VECTOR_SIZE
    edge = Edge(
        source="A", target="B", 
        edge_type=EdgeType.CAUSES, 
        vector=vector
    )
    
    # Base rate = 0.01
    # Emotional (175-209): rate = 0.01 * 0.1 = 0.001. Expected = 0.999
    # Factual (580-639): rate = 0.01 * 2.0 = 0.02. Expected = 0.98
    
    from graph.activation.decay import apply_global_decay
    from graph.graph import CognitiveGraph
    from graph.graph_store import InMemoryGraphStore
    
    graph = CognitiveGraph(InMemoryGraphStore())
    graph.add_edge(edge)
    
    apply_global_decay(graph, rate=0.01)
    
    updated_edge = graph.get_edge("A", "B")
    
    emo_val = updated_edge.vector[RANGE_EMOTIONAL_RANGE[0]]
    fact_val = updated_edge.vector[RANGE_FACTUAL_WORLD[0]]
    
    print(f"Emotional dimension value: {emo_val:.4f}")
    print(f"Factual dimension value: {fact_val:.4f}")
    
    assert abs(emo_val - 0.999) < 0.0001
    assert abs(fact_val - 0.98) < 0.0001
    
    print("Vector Decay Test Passed!")


if __name__ == "__main__":
    test_hebbian_formula()
    test_vector_decay()
