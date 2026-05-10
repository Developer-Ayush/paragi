"""
tests/test_api_integration.py — Verification for Phase 8.
"""
import sys
import os
import time
import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "backend"))

from api.server import app


def test_api_query():
    print("\n[TEST] API Integration: POST /query")
    # Using 'with' triggers the FastAPI lifespan
    with TestClient(app) as client:
        # 1. Send query
        response = client.post("/query", json={"text": "Fire causes heat."})
        assert response.status_code == 200
        data = response.json()
        
        print(f"API Response: {data['answer']}")
        assert "fire" in data['answer'].lower()
        assert "heat" in data['answer'].lower()
        
        # 2. Send linked query
        response = client.post("/query", json={"text": "heat leads to pain."})
        assert response.status_code == 200
        
        # 3. Reasoning query
        response = client.post("/reason", json={"query": "Why is fire dangerous?"})
        assert response.status_code == 200
        data = response.json()
        print(f"Reasoning Response: {data['answer']}")
        
        assert "fire" in data['answer'].lower()
        assert "pain" in data['answer'].lower()
        
        print("Test Passed!")


if __name__ == "__main__":
    test_api_query()
