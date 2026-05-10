from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

router = APIRouter(prefix="/internal", tags=["internal"])

class EncodeRequest(BaseModel):
    text: str

class DecodeRequest(BaseModel):
    question: Optional[str] = None
    graph_answer: Optional[str] = ""
    path: List[Any] = []
    edge_types: List[str] = []
    confidence: float = 0.5
    intent_kind: str = "general"

def check_auth(key: str = Header(None, alias="X-Internal-Key")):
    internal_key = os.getenv("PARAGI_INTERNAL_KEY")
    if not internal_key:
        raise HTTPException(status_code=503, detail="Internal key not configured")
    if not key or key != internal_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/encode")
async def internal_encode(req: EncodeRequest, key: str = Header(None, alias="X-Internal-Key")):
    check_auth(key)
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=422, detail="Text required")
    from api.server import semantic_compiler
    ir = semantic_compiler.compile(req.text)
    return {
        "intent": ir.intent,
        "entities": ir.entities,
        "source": ir.source_concept,
        "target": ir.target_concept,
        "confidence": ir.confidence,
        "fallback_used": False
    }

@router.post("/decode")
async def internal_decode(req: DecodeRequest, key: str = Header(None, alias="X-Internal-Key")):
    check_auth(key)
    if not req.path:
        raise HTTPException(status_code=422, detail="Node path required")
    
    # Compatibility: convert list of dicts to list of node labels
    node_path = []
    for item in req.path:
        if isinstance(item, dict):
            node_path.append(item.get("source") or item.get("target") or "unknown")
        else:
            node_path.append(str(item))

    from api.server import language_generator
    answer = language_generator.generate(
        question=req.question or "",
        graph_answer=req.graph_answer,
        node_path=node_path,
        edge_types=req.edge_types,
        confidence=req.confidence,
        intent_kind=req.intent_kind
    )
    return {"answer": answer, "fallback_used": False}
