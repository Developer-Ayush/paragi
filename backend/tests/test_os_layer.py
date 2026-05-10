"""
tests/test_os_layer.py — Verification for Phase 11.
"""
import sys
import os
import time
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.agent import ParagiAgent


def test_personal_graph_isolation():
    print("\n[TEST] Personal Graph Isolation")
    agent = ParagiAgent()
    
    # 1. Alice tells a personal fact
    res_a = agent.query("My favorite color is Blue.", user_id="alice")
    assert res_a["scope"] == "personal"
    
    # 2. Bob asks about his favorite color
    res_b = agent.query("What is my favorite color?", user_id="bob")
    # Bob hasn't said anything yet, shouldn't find Alice's fact
    assert "blue" not in res_b["answer"].lower()
    
    # 3. Alice asks about her favorite color
    res_a2 = agent.query("What is my favorite color?", user_id="alice")
    print(f"Alice's second answer: {res_a2['answer']}")
    assert "blue" in res_a2["answer"].lower()
    
    print("Isolation Test Passed!")
    agent.shutdown()


def test_cognitive_economy():
    print("\n[TEST] Cognitive Economy (Credits)")
    agent = ParagiAgent()
    
    # 1. Contributor tells a world fact
    # "Fire causes heat" -> 1 relation
    res = agent.query("Fire causes heat.", user_id="contributor_1")
    
    assert res["scope"] == "main"
    assert res["credits_awarded"] == 10
    
    # 2. Check user state
    user = agent.kernel.user_state.get_user("contributor_1")
    # Base 100 + 10 awarded
    assert user["credits"] == 110
    
    print("Economy Test Passed!")
    agent.shutdown()


def test_bloom_filter():
    print("\n[TEST] Bloom Filter")
    from graph.persistence.bloom import BloomFilter
    
    bloom = BloomFilter(size=100)
    bloom.add("existing_concept")
    
    assert bloom.maybe_exists("existing_concept") is True
    assert bloom.maybe_exists("non_existent_concept") is False
    
    print("Bloom Filter Test Passed!")


if __name__ == "__main__":
    test_personal_graph_isolation()
    test_cognitive_economy()
    test_bloom_filter()
