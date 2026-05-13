"""api/routes/health.py — Health and status endpoints."""
from __future__ import annotations
from fastapi import APIRouter
from typing import Any, Dict

router = APIRouter()

@router.get("/")
async def root():
    return {"ok": True, "ui": "http://localhost:3000", "message": "Paragi API is alive"}

@router.get("/domains")
async def domains():
    return {
        "count": 1,
        "domains": [{"id": "general", "name": "General Knowledge", "credit_multiplier": 1.0}]
    }


@router.get("/health")
async def health() -> Dict[str, Any]:
    from api.server import agent
    if agent is None:
        return {"status": "starting"}

    return {
        "status": "ok",
        "node_count": len(agent.kernel.graph._nodes),
        "edge_count": len(agent.kernel.graph._edges),
        "store_kind": type(agent.kernel.store).__name__,
        "llm_backend": agent.kernel.llm.backend if hasattr(agent.kernel, "llm") else "unknown",
    }


@router.get("/llm/status")
async def llm_status() -> Dict[str, Any]:
    from api.server import agent
    if agent is None or not hasattr(agent.kernel, "llm"):
        return {"enabled": False}
    try:
        return agent.kernel.llm.status()
    except Exception as e:
        return {"backend": agent.kernel.llm.backend, "error": str(e)}
