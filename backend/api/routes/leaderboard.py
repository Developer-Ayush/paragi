from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/contributors")
async def contributors_leaderboard(limit: int = 5):
    return {
        "count": 1,
        "items": [
            {"user_id": "alice", "credits": 1000, "rank": 1},
            {"user_id": "bob", "credits": 500, "rank": 2}
        ]
    }

@router.get("/contributors/{domain}")
async def contributors_domain_leaderboard(domain: str, limit: int = 5):
    return {
        "domain": domain,
        "count": 1,
        "items": [
            {"user_id": "bob", "credits": 500, "rank": 1}
        ]
    }

@router.get("/domains")
async def domains_summary():
    return {
        "count": 1,
        "items": [
            {"domain": "legal", "total_nodes": 100, "active_users": 1}
        ]
    }

@router.get("/{domain}")
async def domain_leaderboard(domain: str, limit: int = 5):
    return {
        "domain": domain,
        "count": 1,
        "items": [
            {"user_id": "bob", "credits": 500, "rank": 1}
        ]
    }
