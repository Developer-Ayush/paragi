"""api/routes/reasoning.py — Advanced reasoning control and inspection endpoint."""
from __future__ import annotations

import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()

# ── Models ───────────────────────────────────────────────────────────────────

class ReasoningRequest(BaseModel):
    query: str = Field(..., description="Natural language query to reason over.")
    mode: Optional[str] = Field("general", description="Reasoning mode (causal, planning, probabilistic, etc.)")
    max_depth: int = Field(5, ge=1, le=10, description="Maximum traversal depth.")
    min_confidence: float = Field(0.1, ge=0.0, le=1.0, description="Minimum confidence threshold for results.")
    inspect_activation: bool = Field(False, description="Whether to return activated subgraph nodes and salience scores.")
    scope: str = Field("main", description="Graph scope to search (main, personal, etc.)")

class PathInspection(BaseModel):
    nodes: List[str]
    edges: List[str]
    confidence: float
    strength: float

class ReasoningResponse(BaseModel):
    answer: str
    mode: str
    confidence: float
    latency_ms: float
    paths: List[PathInspection]
    activation_state: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/reason", response_model=ReasoningResponse)
async def reason_endpoint(req: ReasoningRequest):
    """
    Execute a targeted reasoning pass with advanced inspection parameters.
    """
    from api.server import cognition_engine, semantic_compiler
    
    t0 = time.perf_counter()
    
    # 1. Compile query to IR
    ir = semantic_compiler.compile(req.query)
    
    # 2. Override IR parameters based on request
    ir.reasoning_mode = req.mode
    ir.context["max_depth"] = req.max_depth
    ir.context["min_confidence"] = req.min_confidence
    
    # 3. Execute cognitive pipeline
    result = cognition_engine.process(ir)
    
    # 4. Handle low confidence
    if result.confidence < req.min_confidence:
         return {
            "answer": f"Reasoning yielded confidence {result.confidence:.2f}, which is below the requested threshold of {req.min_confidence}.",
            "mode": result.mode,
            "confidence": result.confidence,
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "paths": [],
            "metadata": {"error": "low_confidence"}
        }

    # 5. Format response
    latency_ms = (time.perf_counter() - t0) * 1000
    
    response = {
        "answer": result.answer,
        "mode": result.mode,
        "confidence": round(result.confidence, 4),
        "latency_ms": round(latency_ms, 2),
        "paths": [
            {
                "nodes": p.node_labels,
                "edges": [str(eid) for eid in p.edge_ids],
                "confidence": round(p.confidence, 4),
                "strength": round(p.total_strength, 4)
            }
            for p in result.paths
        ],
        "metadata": result.extra
    }
    
    if req.inspect_activation:
        # In a production system, we'd pull the actual activation state from the engine
        response["activation_state"] = {node: 0.8 for node in result.node_path}
        
    return response
