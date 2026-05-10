"""api/server.py — New FastAPI application for the cognitive graph runtime.

Exposes the same API surface as app/main.py but routes through the new
cognitive architecture: encoder → graph → reasoning → decoder.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth import auth_middleware
from api.middleware.logging import logging_middleware
from api.middleware.metrics import metrics_middleware
from api.middleware.rate_limit import rate_limit_middleware

from core.config import Settings
from core.logger import get_logger
from graph.graph import GraphEngine
from graph.memory.decay import DecayWorker
from graph.memory.working import WorkingMemory
from graph.memory.episodic import EpisodicMemory
from cognition.consciousness import CognitionEngine
from cognition.state_manager import UserStateStore
from encoder.compiler import SemanticCompiler
from decoder.own_decoder import OwnDecoder
from decoder.language_generator import LanguageGenerator
from graph.expansion import ExpansionQueueStore, ExpansionResolver
from graph.expansion_worker import ExpansionWorker

log = get_logger(__name__)

# ── Shared runtime state ───────────────────────────────────────────────────────
settings: Settings
graph_engine: GraphEngine
cognition_engine: CognitionEngine
semantic_compiler: SemanticCompiler
language_generator: LanguageGenerator
user_state_store: UserStateStore
decay_worker: DecayWorker
expansion_worker: ExpansionWorker
llm_refiner: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global settings, graph_engine, cognition_engine, semantic_compiler
    global language_generator, user_state_store, decay_worker, expansion_worker, llm_refiner

    settings = Settings.from_env()
    log.info(f"Paragi cognitive runtime starting | data_dir={settings.data_dir}")

    # ── Build LLM refiner (optional) ──────────────────────────────────────
    if settings.llm_backend in ("ollama", "groq"):
        try:
            from utils.llm_refiner import LLMRefiner  # type: ignore
            llm_refiner = LLMRefiner(
                backend=settings.llm_backend,
                model=settings.llm_model,
                base_url=settings.llm_base_url,
                timeout_seconds=settings.llm_timeout_seconds,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                seed=settings.llm_seed,
                keep_alive=settings.llm_keep_alive,
                api_key=settings.llm_api_key,
            )
            log.info(f"LLM refiner: {settings.llm_backend}/{settings.llm_model}")
        except Exception as e:
            log.warning(f"LLM refiner unavailable: {e}")

    # ── Build graph engine ────────────────────────────────────────────────
    graph_engine = GraphEngine.build_default(settings)
    if graph_engine.count_nodes() == 0:
        seeded = graph_engine.bootstrap_default()
        log.info(f"Graph bootstrapped with {seeded} seed relations")

    # ── Build memory stores ────────────────────────────────────────────────
    working_memory = WorkingMemory()
    episodic_memory = EpisodicMemory(decay_hours=settings.episodic_decay_hours)
    user_state_store = UserStateStore(settings.user_state_path)

    # ── Build cognitive pipeline components ────────────────────────────────
    semantic_compiler = SemanticCompiler(use_fastembed=False, llm_refiner=llm_refiner)
    own_decoder = OwnDecoder(model_path=settings.decoder_model_path)
    language_generator = LanguageGenerator(llm_refiner=llm_refiner, own_decoder=own_decoder)

    # ── Build expansion components ─────────────────────────────────────────
    expansion_queue = ExpansionQueueStore(settings.data_dir / "expansion_queue.json")
    expansion_resolver = ExpansionResolver(graph_engine, expansion_queue, connectors=[]) # TODO: Add connectors
    # Add default connectors if needed
    from utils.external_sources import WikipediaConnector, ConceptNetConnector
    expansion_resolver.connectors.extend([WikipediaConnector(), ConceptNetConnector()])

    cognition_engine = CognitionEngine(
        graph_engine,
        working_memory=working_memory,
        episodic_memory=episodic_memory,
        expansion_queue=expansion_queue,
        expansion_resolver=expansion_resolver,
        learning_confidence_threshold=settings.learning_confidence_threshold,
    )

    # ── Start background workers ─────────────────────────────────────────
    decay_worker = DecayWorker(graph_engine, interval_seconds=settings.decay_interval_seconds)
    decay_worker.start()
    
    expansion_worker = ExpansionWorker(expansion_resolver, interval_seconds=30)
    expansion_worker.start()

    log.info(
        f"Cognitive runtime ready | nodes={graph_engine.count_nodes()} "
        f"edges={graph_engine.count_edges()} llm={settings.llm_backend}"
    )
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    expansion_worker.stop()
    decay_worker.stop()
    graph_engine.close()
    log.info("Paragi cognitive runtime stopped.")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Paragi Cognitive Graph Runtime",
    description="Graph-based cognition engine. Reasoning via traversal, not token generation.",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.middleware("http")(logging_middleware)
app.middleware("http")(metrics_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(auth_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount route modules ────────────────────────────────────────────────────────
from api.routes import query as query_routes  # noqa: E402
from api.routes import graph as graph_routes  # noqa: E402
from api.routes import reasoning as reasoning_routes  # noqa: E402
from api.routes import memory as memory_routes  # noqa: E402
from api.routes import training as training_routes  # noqa: E402
from api.routes import auth as auth_routes  # noqa: E402
from api.routes import expansion as expansion_routes  # noqa: E402
from api.routes import crawler as crawler_routes  # noqa: E402
from api.routes import analytics as analytics_routes  # noqa: E402
from api.routes import leaderboard as leaderboard_routes  # noqa: E402
from api.routes import translator as translator_routes  # noqa: E402
from api.routes import health as health_routes  # noqa: E402

app.include_router(query_routes.router)
app.include_router(graph_routes.router)
app.include_router(reasoning_routes.router)
app.include_router(memory_routes.router)
app.include_router(training_routes.router)
app.include_router(auth_routes.router)
app.include_router(expansion_routes.router, prefix="/expansion")
app.include_router(crawler_routes.router)
app.include_router(analytics_routes.router)
app.include_router(leaderboard_routes.router)
app.include_router(translator_routes.router)
app.include_router(health_routes.router)

def fetch_realtime_answer(query: str):
    """Stub for realtime answers, usually patched in tests."""
    return None, None
