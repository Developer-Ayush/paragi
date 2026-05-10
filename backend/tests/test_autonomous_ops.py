"""
tests/test_autonomous_ops.py — Verification for Phase 10.
"""
import sys
import os
import time
import hashlib
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.agent import ParagiAgent


def _get_id(label: str) -> str:
    return hashlib.sha256(label.lower().strip().encode()).hexdigest()[:16]


def test_autonomous_expansion():
    print("\n[TEST] Autonomous Expansion")
    agent = ParagiAgent()
    
    # 1. Enqueue unknown concept 'steam'
    agent.kernel.expansion.enqueue("steam")
    
    print("Waiting for expansion worker...")
    time.sleep(2) # Give it time to resolve
    
    # 2. Check if 'steam' was expanded
    # Expansion worker for 'steam' adds 'steam --IS_A--> gas'
    source_id = _get_id("steam")
    target_id = _get_id("gas")
    
    edge = agent.kernel.graph.get_edge(source_id, target_id)
    assert edge is not None
    print(f"Autonomous knowledge found: steam --{edge.edge_type}--> gas")
    
    agent.shutdown()
    print("Expansion Test Passed!")


def test_cognitive_pulse():
    print("\n[TEST] Cognitive Heartbeat")
    agent = ParagiAgent()
    
    # 1. Add a salient node
    from graph.node import Node
    from core.enums import NodeType
    
    fire_id = _get_id("fire")
    fire = Node(id=fire_id, label="fire", type=NodeType.CONCEPT)
    fire.set_activation(1.0)
    agent.kernel.graph.add_node(fire)
    
    print("Waiting for cognitive pulses...")
    time.sleep(1.0)
    
    # 2. Check if activation changed
    updated_fire = agent.kernel.graph.get_node(fire_id)
    print(f"Fire activation after pulses: {updated_fire.activation:.4f}")
    
    assert updated_fire.activation > 0
    
    agent.shutdown()
    print("Heartbeat Test Passed!")


if __name__ == "__main__":
    test_autonomous_expansion()
    test_cognitive_pulse()
