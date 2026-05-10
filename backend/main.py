"""backend/main.py — Cognitive Graph Runtime entry point.

Usage:
    python main.py
    uvicorn main:app --reload --port 8000

This replaces `uvicorn app.main:app` as the server entry point.
The original app/ directory is preserved for reference.
"""
from __future__ import annotations

import sys
import os

# Add backend root to Python path so all modules resolve correctly
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from api.server import app  # noqa: E402  (the FastAPI application)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("PARAGI_RELOAD", "1") == "1",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
