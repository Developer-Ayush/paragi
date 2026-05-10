"""api/routes/graph.py — Graph inspection and management endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Any, Dict, List

router = APIRouter(prefix="/graph")


@router.get("/summary")
async def graph_summary() -> Dict[str, Any]:
    from api.server import graph_engine
    nodes = graph_engine.list_nodes(limit=200)
    edges = graph_engine.list_edges(limit=200)
    return {
        "node_count": graph_engine.count_nodes(),
        "edge_count": graph_engine.count_edges(),
        "nodes": [{"id": n.id, "label": n.label, "access_count": n.access_count} for n in nodes[:50]],
        "edges": [{"id": e.id, "source": e.source, "target": e.target, "type": e.type,
                   "strength": round(e.strength, 4)} for e in edges[:100]],
    }


@router.get("/hubs")
async def graph_hubs(limit: int = Query(default=20, ge=1, le=100)) -> List[Dict[str, Any]]:
    from api.server import graph_engine
    hubs = graph_engine.detect_hubs(limit=limit)
    return [{"label": h.node_label, "total_degree": h.total_degree,
             "hub_score": round(h.hub_score, 3)} for h in hubs]


@router.get("/analogies/{label}")
async def graph_analogies(label: str, limit: int = Query(default=5, ge=1, le=20)) -> List[Dict[str, Any]]:
    from api.server import graph_engine
    candidates = graph_engine.find_analogy_candidates(label, limit=limit)
    return [{"candidate": c.candidate_label, "shared": c.shared_neighbors,
             "jaccard": round(c.jaccard, 3)} for c in candidates]


@router.post("/nodes")
async def add_node(body: Dict[str, str]) -> Dict[str, Any]:
    from api.server import graph_engine
    label = body.get("label", "").strip()
    if not label:
        return {"error": "label required"}
    node = graph_engine.create_or_get_node(label)
    return {"id": node.id, "label": node.label}


@router.post("/edges")
async def add_edge(body: Dict[str, Any]) -> Dict[str, Any]:
    from api.server import graph_engine
    from core.enums import EdgeType
    source = str(body.get("source", "")).strip()
    target = str(body.get("target", "")).strip()
    rel = str(body.get("type", "CORRELATES")).upper()
    strength = float(body.get("strength", 0.5))
    if not source or not target:
        return {"error": "source and target required"}
    try:
        etype = EdgeType(rel)
    except ValueError:
        etype = EdgeType.CORRELATES
    edge = graph_engine.create_edge(source, target, etype, strength=strength)
    return {"id": edge.id, "source": source, "target": target, "type": rel}
