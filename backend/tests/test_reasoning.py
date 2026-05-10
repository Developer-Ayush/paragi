"""
tests/test_reasoning.py — Verification for Phase 4.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from graph.node import Node
from graph.edge import Edge
from core.enums import EdgeType, ReasoningMode
from core.semantic_ir import SemanticIR
from reasoning.router import ReasoningRouter


def test_causal_reasoning():
    print("\n[TEST] Causal Reasoning: Why is fire dangerous?")
    
    # 1. Setup Graph: Fire -> burns -> pain -> injury
    store = InMemoryGraphStore()
    graph = CognitiveGraph(store)
    
    def add_fact(s, r, t):
        import hashlib
        sid = hashlib.sha256(s.lower().strip().encode()).hexdigest()[:16]
        tid = hashlib.sha256(t.lower().strip().encode()).hexdigest()[:16]
        if not graph.get_node(sid): graph.add_node(Node(id=sid, label=s))
        if not graph.get_node(tid): graph.add_node(Node(id=tid, label=t))
        graph.add_edge(Edge(source=sid, target=tid, edge_type=r, weight=0.8))
        
    add_fact("Fire", EdgeType.CAUSES, "burns")
    add_fact("burns", EdgeType.CAUSES, "pain")
    add_fact("pain", EdgeType.ASSOCIATED_WITH, "injury")
    
    # 2. Setup Router
    router = ReasoningRouter(graph)
    
    # 3. Create IR
    ir = SemanticIR(
        text="Why is fire dangerous?",
        entities=["Fire"],
        intent="query",
        metadata={"reasoning_mode": ReasoningMode.CAUSAL.value}
    )
    
    # 4. Reason
    result = router.reason(ir)
    print(f"Reasoning Result: {result['chains']}")
    
    assert any("Fire -> burns -> pain -> injury" in chain for chain in result['chains'])
    print("Test Passed!")


def test_analogical_reasoning():
    print("\n[TEST] Analogical Reasoning: Atom is like Solar System")
    
    # 1. Setup Graph:
    # Solar System: Sun -(CENTRAL)-> Planets, Sun -(GRAVITY)-> Planets
    # Atom: Nucleus -(CENTRAL)-> Electrons, Nucleus -(ELECTROMAGNETISM)-> Electrons
    store = InMemoryGraphStore()
    graph = CognitiveGraph(store)
    
    def add_fact(s, r, t):
        import hashlib
        sid = hashlib.sha256(s.lower().strip().encode()).hexdigest()[:16]
        tid = hashlib.sha256(t.lower().strip().encode()).hexdigest()[:16]
        if not graph.get_node(sid): graph.add_node(Node(id=sid, label=s))
        if not graph.get_node(tid): graph.add_node(Node(id=tid, label=t))
        graph.add_edge(Edge(source=sid, target=tid, edge_type=r, weight=0.9))

    add_fact("Solar System", EdgeType.ASSOCIATED_WITH, "Sun")
    add_fact("Sun", EdgeType.CAUSES, "Gravity") # Simplified for test
    
    add_fact("Atom", EdgeType.ASSOCIATED_WITH, "Nucleus")
    add_fact("Nucleus", EdgeType.CAUSES, "Electromagnetism")
    
    # 2. Setup Router
    router = ReasoningRouter(graph)
    
    # 3. Create IR
    ir = SemanticIR(
        text="What is like a Solar System?",
        entities=["Solar System"],
        intent="query",
        metadata={"reasoning_mode": ReasoningMode.ANALOGY.value}
    )
    
    # 4. Reason
    result = router.reason(ir)
    print(f"Analogy Candidates for Solar System: {[c['concept'] for c in result['candidates']]}")
    
    assert any(c['concept'] == "Atom" for c in result['candidates'])
    print("Test Passed!")


if __name__ == "__main__":
    try:
        test_causal_reasoning()
        test_analogical_reasoning()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
