from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import time

router = APIRouter(tags=["training"])

@router.get("/encoder/training/recent")
async def recent_training_records(limit: int = 10):
    return {
        "count": 1,
        "items": [
            {
                "raw_text": "does fire burn?",
                "answer": "fire causes burn",
                "backend": "own",
                "timestamp": time.time()
            }
        ]
    }

@router.post("/encoder/train")
async def train_encoder(params: Dict[str, Any]):
    return {"ok": True, "summary": "Encoder trained on 0 new records"}

@router.post("/decoder/train")
async def train_decoder(params: Dict[str, Any]):
    return {"ok": True, "summary": "Decoder trained on 0 new records", "decoder_backend": "own"}
