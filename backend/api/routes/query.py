"""api/routes/query.py — POST /query — The main cognitive pipeline endpoint."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
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
        question=req.text,
        graph_answer=reasoning_result.answer,
        node_path=reasoning_result.node_path,
        edge_types=list(reasoning_result.paths[0].edge_types if reasoning_result.paths else []),
        confidence=reasoning_result.confidence,
        intent_kind=ir.intent,
    )

    llm_used = bool(final_answer and final_answer != reasoning_result.answer)
    latency_ms = (time.perf_counter() - t0) * 1000

    return {
        "answer": final_answer or reasoning_result.answer or "I don't have information about that yet.",
        "confidence": round(reasoning_result.confidence, 4),
        "node_path": reasoning_result.node_path,
        "reasoning_mode": reasoning_result.mode,
        "query_type": ir.query_type,
        "llm_used": llm_used,
        "latency_ms": round(latency_ms, 2),
    }
