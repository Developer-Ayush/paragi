"""
tests/test_orchestration.py — Verification for Phase 6.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.agent import ParagiAgent


def test_end_to_end_query():
    print("\n[TEST] End-to-End Query: Fire burns skin")
    
    agent = ParagiAgent()
    
    # 1. Teach the agent something
    print("Input 1: Fire causes burns.")
    res1 = agent.query("Fire causes burns.")
    print(f"Response 1: {res1['answer']}")
    
    # 2. Teach another linked fact
    print("Input 2: burns cause injury.")
    res2 = agent.query("burns cause injury.")
    print(f"Response 2: {res2['answer']}")
    
    # 3. Ask a reasoning question
    print("Input 3: Why is fire dangerous?")
    res3 = agent.query("Why is fire dangerous?")
    print(f"Response 3: {res3['answer']}")
    
    # 4. Verify
    assert "fire" in res3['answer'].lower()
    assert "injury" in res3['answer'].lower()
    
    print("Test Passed!")


if __name__ == "__main__":
    try:
        test_end_to_end_query()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
