from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(tags=["analytics"])

@router.get("/users/{user_id}/impact")
async def user_impact(user_id: str):
    return {
        "user_id": user_id,
        "summary": "High impact",
        "personal_memory": {"nodes": 0},
        "main_graph_impact": {"nodes": 0}
    }
