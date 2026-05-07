from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field

from .graph_translator import GraphTranslator

router = APIRouter()

class EncodeRequest(BaseModel):
    text: str = Field(..., min_length=1)

class EncodeResponse(BaseModel):
    source: str
    relation: str
    target: str
    confidence: float
    fallback_used: bool

class DecodeRequest(BaseModel):
    path: List[Dict[str, Any]] = Field(..., min_items=1)
    confidence: float

class DecodeResponse(BaseModel):
    answer: str
    fallback_used: bool

def get_translator(request: Request) -> GraphTranslator:
    translator = getattr(request.app.state, "translator", None)
    if translator is None:
        raise HTTPException(status_code=503, detail="Translator service unavailable")
    return translator

async def verify_internal_key(x_internal_key: str = Header(None)):
    internal_key = os.getenv("PARAGI_INTERNAL_KEY")
    if not internal_key:
        raise HTTPException(status_code=503, detail="Internal routes disabled")
    if x_internal_key != internal_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")

def log_translator_access(metadata: dict[str, Any]) -> None:
    log_path = Path("data/translator_access_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metadata) + "\n")
    except Exception:
        pass

@router.post("/encode", response_model=EncodeResponse, dependencies=[Depends(verify_internal_key)])
async def internal_encode(request: EncodeRequest, translator: GraphTranslator = Depends(get_translator)):
    start_time = time.time()
    try:
        res = translator.encode(request.text)
        latency = time.time() - start_time

        log_translator_access({
            "endpoint": "/internal/encode",
            "timestamp": time.time(),
            "latency": latency,
            "fallback_used": res.get("fallback_used", False)
        })

        return EncodeResponse(
            source=res["source"],
            relation=res["relation"],
            target=res["target"],
            confidence=res["confidence"],
            fallback_used=res.get("fallback_used", False)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encoding failed: {str(e)}")

@router.post("/decode", response_model=DecodeResponse, dependencies=[Depends(verify_internal_key)])
async def internal_decode(request: DecodeRequest, translator: GraphTranslator = Depends(get_translator)):
    start_time = time.time()
    try:
        answer, fallback_used = translator.decode(request.path, request.confidence)
        if not answer:
             raise HTTPException(status_code=503, detail="Model unavailable and fallback failed")

        latency = time.time() - start_time

        log_translator_access({
            "endpoint": "/internal/decode",
            "timestamp": time.time(),
            "latency": latency,
            "fallback_used": fallback_used
        })

        return DecodeResponse(
            answer=answer,
            fallback_used=fallback_used
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decoding failed: {str(e)}")
