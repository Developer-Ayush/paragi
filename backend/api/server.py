"""
api/server.py — FastAPI application for the cognitive graph runtime.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.agent import ParagiAgent
from core.logger import get_logger

log = get_logger(__name__)

# ── Shared runtime state ───────────────────────────────────────────────────────
agent: Optional[ParagiAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    log.info("Paragi cognitive runtime starting...")
    
    # 1. Initialize the new ParagiAgent (Kernel handles sub-components)
    agent = ParagiAgent()
    
    log.info("Cognitive runtime ready.")
    yield
    
    # 2. Shutdown
    agent.shutdown()
    log.info("Paragi cognitive runtime stopped.")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Paragi Cognitive Graph Runtime",
    description="Graph-based cognition engine. Reasoning via traversal, not token generation.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount route modules ────────────────────────────────────────────────────────
from api.routes import query as query_routes
from api.routes import reasoning as reasoning_routes
from api.routes import auth as auth_routes
from api.routes import health as health_routes

app.include_router(query_routes.router)
app.include_router(reasoning_routes.router)
app.include_router(auth_routes.router)
app.include_router(health_routes.router)
