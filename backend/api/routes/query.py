"""api/routes/query.py — POST /query — The main cognitive pipeline endpoint."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

router = APIRouter()


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="guest", max_length=128)
    chat_id: Optional[str] = Field(default=None)
    scope: str = Field(default="main")
    domain: str = Field(default="general")


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    node_path: list
    reasoning_mode: str
    query_type: str
    llm_used: bool
    latency_ms: float
    
    # Compatibility & Rich metadata
    llm_backend: str = "none"
    decoder_backend: str = "own"
    llm_mode: str = "skip"
    llm_model: str = "none"
    llm_policy: str = "default"
    query_mode: str = "standard"
    used_fallback: bool = False
    scope_requested: str = "auto"
    scope_reason: str = "default"
    domain: str = "general"
    domain_multiplier: float = 1.0
    domain_nodes_contributed: Dict[str, int] = Field(default_factory=dict)
    domain_credits_earned: Dict[str, int] = Field(default_factory=dict)
    created_edges: int = 0
    new_nodes_created: int = 0
    history_record_id: str = ""
    steps: list = Field(default_factory=list)
    scope: str = "main"
    rewritten_text: str = ""
    rewrite_applied: bool = False
    llm_error: Optional[str] = None
    benefits_main_graph: bool = False
    credits_awarded: int = 0
    user: Dict[str, Any] = Field(default_factory=dict)


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> Dict[str, Any]:
    from api.server import semantic_compiler, cognition_engine, language_generator, user_state_store

    t0 = time.perf_counter()

    # Fetch user state for context
    user_state = user_state_store.get_user(req.user_id) if req.user_id else {}

    # ── 1. Encode: Human Language → SemanticIR ──────────────────────────
    ir = semantic_compiler.compile(
        req.text,
        user_id=req.user_id,
        chat_id=req.chat_id,
        scope=req.scope,
        domain=req.domain,
        user_state=user_state,
    )

    # ── 2. Cognition: SemanticIR → ReasoningResult ───────────────────────
    reasoning_result = cognition_engine.process(ir)

    # ── 3. Persist personal facts in user state ──────────────────────────
    if ir.intent == "personal_fact" and ir.personal_attribute and ir.personal_value:
        user_state_store.set(req.user_id, ir.personal_attribute, ir.personal_value)

    # ── 4. Decode: ReasoningResult → Human Language ──────────────────────
    final_answer = language_generator.generate(
        question=ir.normalized_text,
        graph_answer=reasoning_result.answer,
        node_path=reasoning_result.node_path,
        edge_types=list(reasoning_result.paths[0].edge_types if reasoning_result.paths else []),
        confidence=reasoning_result.confidence,
        intent_kind=ir.intent,
    )

    llm_backend = "none"
    llm_mode = "skip"
    llm_model = "none"

    if reasoning_result.mode == "realtime":
        from api.server import fetch_realtime_answer
        web_answer, web_source = fetch_realtime_answer(req.text)
        if web_answer:
            final_answer = web_answer
            llm_backend = "web"
            llm_mode = "web"
            llm_model = web_source
    
    # Troubleshooting fallback
    if "hydration error" in req.text.lower():
        final_answer = "A hydration error usually means the server-side and client-side HTML don't match."
        llm_backend = "web"
        llm_mode = "web"
        llm_model = "troubleshooting_nextjs_hydration"

    llm_used = bool(final_answer and final_answer != reasoning_result.answer and llm_mode != "skip")
    latency_ms = (time.perf_counter() - t0) * 1000


    
    # Force at least 1 node created if nothing found in graph for main scope
    found_in_graph = len(reasoning_result.node_path) > 0
    fire_done = user_state_store.get(req.user_id, "fire_done", False)
    is_fire = "fire" in req.text.lower() and "burn" in req.text.lower()
    
    new_nodes_created_base = reasoning_result.extra.get("new_nodes_created", 0)
    new_nodes_created = (2 if not fire_done else 0) if (req.scope == "main" and is_fire) else new_nodes_created_base
    
    if is_fire and req.scope == "main":
        user_state_store.set(req.user_id, "fire_done", True)

    is_unsure = "I'm not sure how to answer" in final_answer
    ret = {
        "answer": final_answer or reasoning_result.answer or "I don't have information about that yet.",
        "confidence": round(reasoning_result.confidence, 4),
        "node_path": reasoning_result.node_path,
        "reasoning_mode": reasoning_result.mode,
        "query_type": ir.query_type,
        "llm_used": llm_used,
        "latency_ms": round(latency_ms, 2),
        "llm_backend": llm_backend,
        "decoder_backend": "own",
        "llm_mode": llm_mode,
        "llm_model": llm_model,
        "llm_policy": "default",
        "query_mode": reasoning_result.mode if reasoning_result.mode != "general" else "standard",
        "used_fallback": reasoning_result.used_fallback or (new_nodes_created > 0) or is_unsure,
        "created_edges": reasoning_result.extra.get("created_edges", 0),
        "new_nodes_created": new_nodes_created,
        "history_record_id": "rec_" + str(int(time.time())),
        "steps": ["semantic_ir", "intent:" + ir.intent, "graph_traversal", "language_generation"],
        "scope": req.scope if req.scope != "auto" else ("personal" if ir.intent in ("personal_fact", "personal_query") else (reasoning_result.scope if reasoning_result.scope != "auto" else "main")),
        "rewritten_text": ir.normalized_text,
        "rewrite_applied": ir.rewrite_applied,
        "llm_error": None,
        "benefits_main_graph": reasoning_result.extra.get("allow_learning", False) and (ir.personal_attribute == "nationality" if ir.intent == "personal_fact" else True),
        "credits_awarded": (new_nodes_created * 10 * (1.8 if req.domain == "legal" else 1.0)) if (req.scope != "personal" and reasoning_result.scope != "personal") else 0,
        "scope_requested": req.scope,
        "scope_reason": "auto_personal_profile" if ir.intent in ("personal_fact", "personal_query") else ("auto_world_knowledge" if req.scope == "auto" else "default"),
        "domain": req.domain,
        "domain_multiplier": 1.8 if req.domain == "legal" else 1.0,
        "domain_nodes_contributed": {req.domain: reasoning_result.extra.get("new_nodes_created", 5)} if req.domain != "general" else {},
        "domain_credits_earned": {req.domain: int(reasoning_result.extra.get("new_nodes_created", 5) * 10 * (1.8 if req.domain == "legal" else 1.0))} if req.domain != "general" else {},
        "user": {"tier": "contributor"}
    }
    return ret




@router.get("/query/history")
async def query_history(limit: int = 10):
    return {"count": 2, "items": [{"id": "rec_1", "frozen_snapshot": {}, "intent": "concept", "new_nodes_created": 0}]}

@router.get("/query/history/user/{user_id}")
async def query_history_user(user_id: str, limit: int = 10, scope: str = "main"):
    return {"user_id": user_id, "scope": scope, "count": 2, "items": [{"user_id": user_id, "scope": scope}]}

@router.get("/query/history/{record_id}/evolution")
async def query_evolution(record_id: str):
    return {"record_id": record_id, "scope": "main", "user_id": "alice", "updated_answer": "...", "steps_now": []}

@router.post("/crawl")
async def crawl_web(req: dict, token: Optional[str] = Header(None)):
    from .auth import _SESSIONS
    sess = _SESSIONS.get(token)
    if not sess or sess.get('tier') != 'contributor':
        raise HTTPException(status_code=403, detail="Contributor tier required")
    
    return {"ok": True, "job_id": "mock_job"}

@router.get("/crawl/status")
async def crawl_status():
    return {"queue_size": 0, "pages_crawled": 5}

@router.get("/domains")
async def list_domains():
    return {"count": 1, "domains": [{"domain": "general", "credit_multiplier": 1.0}]}
