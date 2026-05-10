"""api/routes/graph.py — Graph inspection and management endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List

router = APIRouter()


@router.get("/graph/summary")
async def graph_summary(scope: str = "main") -> Dict[str, Any]:
    from api.server import graph_engine
    nodes = graph_engine.list_nodes(limit=200)
    edges = graph_engine.list_edges(limit=200)
    return {
        "scope": scope,
        "stats": {
            "node_count": graph_engine.count_nodes(),
            "edge_count": graph_engine.count_edges(),
        },
        "nodes": [{"id": n.id, "label": n.label, "access_count": n.access_count, "description": n.label} for n in nodes[:50]],
        "edges": [{"id": e.id, "source": e.source, "target": e.target, "type": e.type,
                   "strength": round(e.strength, 4), "description": f"{e.source} {e.type} {e.target}", "relation_text": e.type} for e in edges[:100]],
    }


@router.get("/graph/hubs")
async def graph_hubs(limit: int = Query(default=20, ge=1, le=100)) -> Dict[str, Any]:
    from api.server import graph_engine
    hubs = graph_engine.detect_hubs(limit=limit)
    items = [{"label": h.node_label, "total_degree": h.total_degree,
              "hub_score": round(h.hub_score, 3)} for h in hubs]
    return {"count": len(items), "items": items}


@router.get("/reasoning/analogies/{label}")
async def graph_analogies(label: str, limit: int = Query(default=5, ge=1, le=20)) -> Dict[str, Any]:
    from api.server import graph_engine
    candidates = graph_engine.find_analogy_candidates(label, limit=limit)
    items = [{"candidate": c.candidate_label, "shared_neighbors": c.shared_neighbors,
              "jaccard": round(c.jaccard, 3)} for c in candidates]
    return {"count": len(items), "items": items}


class NodeCreate(BaseModel):
    label: str

class EdgeCreate(BaseModel):
    source: str
    target: str
    type: str = "CORRELATES"
    strength: float = 0.5

@router.post("/nodes")
async def add_node(body: NodeCreate) -> Dict[str, Any]:
    from api.server import graph_engine
    label = body.label.strip()
    if not label:
        return {"error": "label required"}
    node = graph_engine.create_or_get_node(label)
    return {"id": node.id, "label": node.label}


@router.post("/edges")
async def add_edge(body: EdgeCreate) -> Dict[str, Any]:
    from api.server import graph_engine
    from core.enums import EdgeType
    source = body.source.strip()
    target = body.target.strip()
    rel = body.type.upper()
    strength = body.strength
    if not source or not target:
        return {"error": "source and target required"}
    try:
        etype = EdgeType(rel)
    except ValueError:
        etype = EdgeType.CORRELATES
    edge = graph_engine.create_edge(source, target, etype, strength=strength)
    return {"id": edge.id, "source": source, "target": target, "type": rel}
