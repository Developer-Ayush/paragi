"""
api/routes/reasoning.py — Reasoning control and inspection endpoint.
"""
from __future__ import annotations

import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ReasoningRequest(BaseModel):
    query: str = Field(..., description="Natural language query to reason over.")
    mode: Optional[str] = Field("general", description="Reasoning mode.")


@router.post("/reason")
async def reason_endpoint(req: ReasoningRequest):
    """
    Execute a targeted reasoning pass.
    """
    from api.server import agent
    
    t0 = time.perf_counter()
    
    # Execute cognitive pipeline
    result = agent.query(req.query)
    
    latency_ms = (time.perf_counter() - t0) * 1000
    
    # Extend response with latency
    result["latency_ms"] = round(latency_ms, 2)
    
    return result
