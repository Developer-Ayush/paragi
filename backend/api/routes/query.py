"""
api/routes/query.py — The main cognitive pipeline endpoint.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="guest", max_length=128)


@router.post("/query")
async def query_endpoint(req: QueryRequest) -> Dict[str, Any]:
    """
    Primary endpoint for user interaction with the cognitive system.
    """
    from api.server import agent
    
    t0 = time.perf_counter()
    
    # Execute full cognitive cycle with user context
    result = agent.query(req.text, user_id=req.user_id)
    
    latency_ms = (time.perf_counter() - t0) * 1000
    
    # Add timing metadata
    result["latency_ms"] = round(latency_ms, 2)
    
    return result
