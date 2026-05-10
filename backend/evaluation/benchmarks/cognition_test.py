"""
evaluation/benchmarks/cognition_test.py — Activation and Causal Benchmark.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from synthetic.training.generator import SyntheticGraphGenerator
from synthetic.training.scenarios import load_water_cycle
from graph.activation.spread import spread_activation


def run_activation_benchmark():
    print("\n[BENCHMARK] Activation Spread: Water Cycle")
    
    # 1. Setup
    graph = CognitiveGraph(InMemoryGraphStore())
    gen = SyntheticGraphGenerator(graph)
    load_water_cycle(gen)
    
    # 2. Pulse Sun
    print("Pulsing 'Sun' with activation...")
    spread_activation(graph, gen._get_id("Sun"), initial_energy=1.0, max_hops=10)
    
    # 3. Check reach
    target = "Ocean"
    target_node = graph.get_node(gen._get_id(target))
    activation = target_node.activation if target_node else 0
    
    print(f"Activation at '{target}' after 7 hops: {activation:.4f}")
    
    if activation > 0:
        print("RESULT: SUCCESS - Activation reached target.")
    else:
        print("RESULT: FAIL - Activation blocked.")


if __name__ == "__main__":
    run_activation_benchmark()
