"""
evaluation/benchmarks/analogy_test.py — Analogy Mapping Benchmark.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from synthetic.training.generator import SyntheticGraphGenerator
from synthetic.training.scenarios import load_atom_solar_analogy
from reasoning.analogy_reasoner import AnalogyReasoner
from core.semantic_ir import SemanticIR


def run_analogy_benchmark():
    print("\n[BENCHMARK] Structural Analogy: Solar System vs Atom")
    
    # 1. Setup
    graph = CognitiveGraph(InMemoryGraphStore())
    gen = SyntheticGraphGenerator(graph)
    load_atom_solar_analogy(gen)
    
    # 2. Query Analogy
    reasoner = AnalogyReasoner(graph)
    ir = SemanticIR(
        text="What is like the Solar System?",
        entities=["Solar System"],
        intent="query"
    )
    
    # 3. Verify mapping
    result = reasoner.reason(ir)
    candidates = [c['concept'] for c in result.get('candidates', [])]
    
    print(f"Analogies found: {candidates}")
    
    if "Atom" in candidates:
        print("RESULT: SUCCESS - Structural analogy identified.")
    else:
        print("RESULT: FAIL - Structural analogy missed.")


if __name__ == "__main__":
    run_analogy_benchmark()
