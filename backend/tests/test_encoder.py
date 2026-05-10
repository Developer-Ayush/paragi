"""
tests/test_encoder.py — Verification for Phase 2.
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from encoder.compiler import SemanticCompiler
from core.enums import EdgeType, ReasoningMode


def test_full_pipeline():
    print("\n[TEST] Full Encoder Pipeline")
    
    compiler = SemanticCompiler() # No graph for pure IR test
    
    text = "Fire causes heat and it leads to pain."
    print(f"Input: {text}")
    
    ir = compiler.compile(text, update_graph=False)
    
    print(f"Detected Intent: {ir.intent}")
    print(f"Detected Mode: {ir.metadata.get('reasoning_mode')}")
    print(f"Extracted Entities: {ir.entities}")
    print(f"Extracted Relations:")
    for rel in ir.relations:
        print(f"  {rel.source} --{rel.relation}--> {rel.target}")
    
    # Assertions
    assert ir.intent in ("assertion", "query")
    assert ir.metadata.get('reasoning_mode') == ReasoningMode.CAUSAL.value
    
    # Check for causal relations
    causal_rels = [r for r in ir.relations if r.relation == EdgeType.CAUSES]
    assert len(causal_rels) >= 1
    
    print("Test Passed!")


if __name__ == "__main__":
    try:
        test_full_pipeline()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
