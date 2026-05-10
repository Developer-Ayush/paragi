from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class MemoryStats(BaseModel):
    working_memory_keys: int
    episodic_memory_count: int
    semantic_density: float

@router.get("/memory/stats", response_model=MemoryStats)
async def memory_stats():
    from api.server import cognition_engine, graph_engine
    
    return {
        "working_memory_keys": len(cognition_engine.working_memory.get_all()),
        "episodic_memory_count": cognition_engine.episodic_memory.count(),
        "semantic_density": graph_engine.count_edges() / max(1, graph_engine.count_nodes())
    }

@router.post("/memory/clear")
async def clear_working_memory():
    from api.server import cognition_engine
    cognition_engine.working_memory.clear()
    return {"status": "ok"}
