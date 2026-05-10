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
    from api.server import graph_engine, settings
    return {
        "status": "ok",
        "node_count": graph_engine.count_nodes(),
        "edge_count": graph_engine.count_edges(),
        "store_kind": graph_engine.store_kind,
        "llm_backend": settings.llm_backend,
    }


@router.get("/llm/status")
async def llm_status() -> Dict[str, Any]:
    from api.server import llm_refiner, settings
    if llm_refiner is None:
        return {"backend": settings.llm_backend, "enabled": False}
    try:
        return llm_refiner.status()
    except Exception as e:
        return {"backend": settings.llm_backend, "error": str(e)}
