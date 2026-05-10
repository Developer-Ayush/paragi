"""
tests/test_core_foundation.py — Verification for Phase 1.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.semantic_ir import SemanticIR, IRRelation
from core.enums import EdgeType, NodeType
from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from graph.graph_builder import GraphBuilder
from graph.traversal.bfs import bfs


def test_fire_burns_skin():
    print("\n[TEST] Fire burns skin example")
    
    # 1. Setup Graph
    store = InMemoryGraphStore()
    graph = CognitiveGraph(store)
    builder = GraphBuilder(graph)
    
    # 2. Create SemanticIR
    ir = SemanticIR(
        text="Fire burns skin.",
        entities=["Fire", "skin"],
        concepts=["burns"],
        relations=[
            IRRelation(source="Fire", relation=EdgeType.CAUSES, target="burns"),
            IRRelation(source="burns", relation=EdgeType.ASSOCIATED_WITH, target="skin")
        ],
        intent="fact_assertion",
        confidence=1.0
    )
    
    # 3. Compile to Graph
    print("Compiling IR to Graph...")
    builder.compile(ir)
    
    # 4. Verify Nodes
    fire_id = builder._generate_id("Fire")
    skin_id = builder._generate_id("skin")
    burns_id = builder._generate_id("burns")
    
    fire_node = graph.get_node(fire_id)
    skin_node = graph.get_node(skin_id)
    burns_node = graph.get_node(burns_id)
    
    assert fire_node is not None, "Fire node missing"
    assert skin_node is not None, "Skin node missing"
    assert burns_node is not None, "Burns node missing"
    print(f"Nodes verified: {fire_node.label}, {burns_node.label}, {skin_node.label}")
    
    # 5. Verify Edges
    edge1 = graph.get_edge(fire_id, burns_id)
    edge2 = graph.get_edge(burns_id, skin_id)
    
    assert edge1 is not None and edge1.edge_type == EdgeType.CAUSES
    assert edge2 is not None and edge2.edge_type == EdgeType.ASSOCIATED_WITH
    print(f"Edges verified: {edge1.edge_type}, {edge2.edge_type}")
    
    # 6. Verify Traversal
    print("Running BFS Traversal from Fire...")
    path = bfs(graph, fire_id, max_depth=2)
    print(f"Traversal path: {[graph.get_node(nid).label for nid in path]}")
    assert path == [fire_id, burns_id, skin_id]
    
    print("Test Passed!")


if __name__ == "__main__":
    try:
        test_fire_burns_skin()
    except Exception as e:
        print(f"Test Failed: {e}")
        sys.exit(1)
