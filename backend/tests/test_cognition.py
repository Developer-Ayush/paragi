"""
tests/test_cognition.py — Verification for Phase 3.
"""
import sys
import os
import time
sys.path.append(os.path.join(os.getcwd(), "backend"))

from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from graph.node import Node
from graph.edge import Edge
from core.enums import EdgeType
from graph.activation.spread import spread_activation
from graph.activation.salience import get_salient_nodes
from graph.activation.decay import apply_temporal_decay


def test_spreading_activation():
    print("\n[TEST] Spreading Activation")
    
    # 1. Setup Graph: Fire -> Heat -> Pain
    store = InMemoryGraphStore()
    graph = CognitiveGraph(store)
    
    n_fire = Node(id="fire", label="Fire")
    n_heat = Node(id="heat", label="Heat")
    n_pain = Node(id="pain", label="Pain")
    
    graph.add_node(n_fire)
    graph.add_node(n_heat)
    graph.add_node(n_pain)
    
    graph.add_edge(Edge(source="fire", target="heat", edge_type=EdgeType.CAUSES, weight=0.8))
    graph.add_edge(Edge(source="heat", target="pain", edge_type=EdgeType.CAUSES, weight=0.7))
    
    # 2. Spread Activation from Fire
    print("Spreading activation from 'Fire'...")
    deltas = spread_activation(graph, "fire", initial_energy=1.0)
    
    print(f"Activation Deltas: {deltas}")
    
    # 3. Verify
    assert graph.get_node("fire").activation > 0.9
    assert graph.get_node("heat").activation > 0.3 # 1.0 * 0.8 * 0.5
    assert graph.get_node("pain").activation > 0.1 # 0.4 * 0.7 * 0.5
    
    print(f"Fire activation: {graph.get_node('fire').activation}")
    print(f"Heat activation: {graph.get_node('heat').activation}")
    print(f"Pain activation: {graph.get_node('pain').activation}")
    
    # 4. Test Salience
    salient = get_salient_nodes(graph, limit=5)
    print(f"Salient nodes: {salient}")
    assert salient[0][0] == "fire"
    
    # 5. Test Decay
    print("Applying temporal decay...")
    apply_temporal_decay(graph, activation_decay_rate=0.5)
    print(f"Fire activation after decay: {graph.get_node('fire').activation}")
    assert graph.get_node("fire").activation < 0.6
    
    print("Test Passed!")


if __name__ == "__main__":
    try:
        test_spreading_activation()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
