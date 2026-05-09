from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .auth_store import AuthStore
from .config import Settings
from .conversation_store import ConversationStore
from .decay_worker import DecayWorker
from .domain_policy import available_domains, credit_multiplier, detect_domain, normalize_domain
from .encoder_training import EncoderTrainingStore
from .expansion import ExpansionQueueStore, ExpansionResolver
from .expansion_worker import ExpansionWorker
from .external_sources import ConceptNetConnector, SemanticScholarConnector, WikipediaConnector
from .graph import GraphEngine
from .graph_translator import GraphTranslator
from .crawler import ParagiCrawler
from .metrics_store import MetricsStore
from .llm_refiner import LLMRefiner, RefineResult
from .models import EdgeType
from .own_decoder import OwnDecoder
from .own_encoder import OwnEncoder
from .personal_graphs import PersonalGraphManager
from .query_control import QueryClassifier
from .realtime_lookup import fetch_realtime_answer, fetch_troubleshooting_answer
from .query_pipeline import QueryPipeline, TemporaryDecoder, TemporaryEncoder
from .query_mode import decide_query_mode
from .query_rewriter import QueryRewriter
from .scope_policy import decide_scope
from .user_state import UserStateStore, sanitize_user_id
from . import translator_routes


class NodeCreateRequest(BaseModel):
    label: str = Field(..., min_length=1)


class EdgeCreateRequest(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    type: EdgeType = EdgeType.CORRELATES
    strength: float = Field(default=0.1, ge=0.0, le=1.0)


class PathQueryRequest(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    max_hops: int = Field(default=7, ge=1, le=12)
    max_paths: int = Field(default=64, ge=1, le=512)
    goal_relevance: float = Field(default=1.0, ge=0.0, le=10.0)


class ConsensusRequest(BaseModel):
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    max_hops: int = Field(default=7, ge=1, le=12)
    max_paths: int = Field(default=64, ge=1, le=512)
    cause_threshold: int = Field(default=3, ge=1, le=20)
    auto_upgrade: bool = True


class ContradictionRequest(BaseModel):
    source: str = Field(..., min_length=1)
    positive_target: str = Field(..., min_length=1)
    negative_target: str = Field(..., min_length=1)
    max_hops: int = Field(default=7, ge=1, le=12)
    max_paths: int = Field(default=64, ge=1, le=512)
    weaken_factor: float = Field(default=0.9, gt=0.0, le=1.0)


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    user_id: str = Field(default="guest", min_length=1, max_length=64)
    scope: str = Field(default="auto", pattern="^(auto|main|personal)$")
    domain: str = Field(default="auto", min_length=1, max_length=32)
    max_hops: int = Field(default=7, ge=1, le=12)
    max_paths: int = Field(default=64, ge=1, le=512)


class UserRegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    tier: str = Field(default="free", pattern="^(free|paid|contributor)$")


class CrawlRequest(BaseModel):
    url: str = Field(..., min_length=1)


class AuthRegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)
    tier: str = Field(default="free", pattern="^(free|paid|contributor)$")


class AuthLoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class AuthLogoutRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=128)


class AuthGoogleRequest(BaseModel):
    credential: str = Field(..., min_length=10)


class EncoderTrainRequest(BaseModel):
    max_records: int = Field(default=50000, ge=100, le=2000000)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    min_token_occurrences: int = Field(default=2, ge=1, le=100)


class DecoderTrainRequest(BaseModel):
    max_records: int = Field(default=50000, ge=100, le=2000000)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    min_samples: int = Field(default=20, ge=1, le=1000)


def _initialize_state(app: FastAPI, *, start_workers: bool) -> None:
    if getattr(app.state, "initialized", False):
        return

    settings = Settings.from_env()
    graph = GraphEngine.build_default(settings)
    decay_worker = DecayWorker(graph, settings.decay_interval_seconds)

    expansion_queue = ExpansionQueueStore(settings.expansion_queue_path)
    connectors = [ConceptNetConnector(), SemanticScholarConnector(), WikipediaConnector()]
    expansion_resolver = ExpansionResolver(graph, expansion_queue, connectors)
    expansion_worker = ExpansionWorker(expansion_resolver, settings.expansion_interval_seconds)

    if settings.encoder_backend == "own":
        encoder = OwnEncoder(model_path=settings.encoder_model_path)
    elif settings.encoder_backend == "fastembed":
        encoder = TemporaryEncoder(use_fastembed=True)
    else:
        encoder = TemporaryEncoder(use_fastembed=False)

    if settings.decoder_backend == "own":
        decoder = OwnDecoder(model_path=settings.decoder_model_path)
    else:
        decoder = TemporaryDecoder()
    classifier = QueryClassifier()
    translator = GraphTranslator(model_name="phi3", data_dir=settings.data_dir)
    crawler = ParagiCrawler(graph, translator)
    pipeline = QueryPipeline(
        graph,
        encoder,
        decoder,
        classifier=classifier,
        expansion_queue=expansion_queue,
        expansion_resolver=expansion_resolver,
    )
    history = ConversationStore(settings.query_history_path)
    encoder_training = EncoderTrainingStore(settings.encoder_training_path)
    query_rewriter = QueryRewriter(settings.query_rewriter_path)
    user_state = UserStateStore(settings.user_state_path)
    auth_store = AuthStore(settings.auth_users_path, settings.auth_sessions_path)
    personal_graphs = PersonalGraphManager(settings)
    metrics_store = MetricsStore(settings.metrics_path)
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

    app.state.settings = settings
    app.state.graph = graph
    app.state.decay_worker = decay_worker
    app.state.expansion_queue = expansion_queue
    app.state.expansion_resolver = expansion_resolver
    app.state.expansion_worker = expansion_worker
    app.state.query_pipeline = pipeline
    app.state.conversation_store = history
    app.state.encoder_training_store = encoder_training
    app.state.query_rewriter = query_rewriter
    app.state.user_state = user_state
    app.state.auth_store = auth_store
    app.state.personal_graphs = personal_graphs
    app.state.metrics_store = metrics_store
    app.state.llm_refiner = llm_refiner
    app.state.translator = translator
    app.state.crawler = crawler
    app.state.initialized = True

    if start_workers:
        decay_worker.start()
        expansion_worker.start()


def _shutdown_state(app: FastAPI) -> None:
    if not getattr(app.state, "initialized", False):
        return
    decay_worker = getattr(app.state, "decay_worker", None)
    expansion_worker = getattr(app.state, "expansion_worker", None)
    graph = getattr(app.state, "graph", None)
    personal_graphs = getattr(app.state, "personal_graphs", None)
    if decay_worker is not None:
        decay_worker.stop()
    if expansion_worker is not None:
        expansion_worker.stop()
    if graph is not None:
        graph.close()
    if personal_graphs is not None:
        personal_graphs.close()
    app.state.initialized = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_state(app, start_workers=True)
    yield
    _shutdown_state(app)


app = FastAPI(
    title="Paragi Prototype API",
    description="Graph storage, reasoning, dynamic activation, expansion nodes, and phase-3 query pipeline.",
    version="0.4.0",
    lifespan=lifespan,
)
app.include_router(translator_routes.router, prefix="/internal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_graph(request: Request) -> GraphEngine:
    if not getattr(request.app.state, "initialized", False):
        _initialize_state(request.app, start_workers=False)
    return request.app.state.graph


def get_pipeline(request: Request) -> QueryPipeline:
    _ = get_graph(request)
    return request.app.state.query_pipeline


def get_conversation_store(request: Request) -> ConversationStore:
    _ = get_graph(request)
    return request.app.state.conversation_store


def get_expansion_queue(request: Request) -> ExpansionQueueStore:
    _ = get_graph(request)
    return request.app.state.expansion_queue


def get_expansion_resolver(request: Request) -> ExpansionResolver:
    _ = get_graph(request)
    return request.app.state.expansion_resolver


def get_encoder_training_store(request: Request) -> EncoderTrainingStore:
    _ = get_graph(request)
    return request.app.state.encoder_training_store


def get_query_rewriter(request: Request) -> QueryRewriter:
    _ = get_graph(request)
    return request.app.state.query_rewriter


def get_user_state(request: Request) -> UserStateStore:
    _ = get_graph(request)
    return request.app.state.user_state


def get_auth_store(request: Request) -> AuthStore:
    _ = get_graph(request)
    return request.app.state.auth_store


def get_personal_graphs(request: Request) -> PersonalGraphManager:
    _ = get_graph(request)
    return request.app.state.personal_graphs


def get_llm_refiner(request: Request) -> LLMRefiner:
    _ = get_graph(request)
    return request.app.state.llm_refiner


def get_metrics_store(request: Request) -> MetricsStore:
    _ = get_graph(request)
    return request.app.state.metrics_store


def get_crawler(request: Request) -> ParagiCrawler:
    _ = get_graph(request)
    return request.app.state.crawler


def get_pipeline_for_scope(request: Request, *, scope: str, user_id: str) -> QueryPipeline:
    safe_user_id = sanitize_user_id(user_id)
    if scope == "personal":
        return get_personal_graphs(request).get_pipeline(safe_user_id)
    return get_pipeline(request)


def get_graph_for_scope(request: Request, *, scope: str, user_id: str) -> GraphEngine:
    safe_user_id = sanitize_user_id(user_id)
    if scope == "personal":
        return get_personal_graphs(request).get_pipeline(safe_user_id).graph
    return get_graph(request)


def _describe_node_for_summary(*, node_label: str, outgoing: list[dict], incoming: list[dict]) -> str:
    outgoing_top = sorted(outgoing, key=lambda item: item["strength"], reverse=True)[:2]
    incoming_top = sorted(incoming, key=lambda item: item["strength"], reverse=True)[:2]

    segments: list[str] = [f"Node '{node_label}'."]
    if outgoing_top:
        items = [
            f"{edge['relation_text']} {edge['target_label']} ({edge['strength']:.2f})"
            for edge in outgoing_top
        ]
        segments.append(f"Outgoing: {', '.join(items)}.")
    if incoming_top:
        items = [
            f"{edge['source_label']} {edge['relation_text']} this node ({edge['strength']:.2f})"
            for edge in incoming_top
        ]
        segments.append(f"Incoming: {', '.join(items)}.")
    if not outgoing_top and not incoming_top:
        segments.append("No visible edges in the selected summary window.")
    return " ".join(segments)


@app.get("/")
def root_info() -> dict:
    return {
        "service": "Paragi Prototype API",
        "ok": True,
        "ui": "Use frontend app on http://localhost:3000",
    }


@app.get("/health")
def health(request: Request) -> dict:
    graph = get_graph(request)
    settings = request.app.state.settings
    metrics = get_metrics_store(request)
    return {
        "ok": True,
        "store": graph.store_kind,
        "persistent_memory": graph.store_kind != "InMemoryGraphStore",
        "hdf5_path": str(settings.hdf5_path),
        "metrics": metrics.get_summary(window_seconds=86400) # Last 24h
    }


@app.get("/llm/status")
def llm_status(request: Request) -> dict:
    payload = get_llm_refiner(request).status()
    payload["policy"] = request.app.state.settings.llm_policy
    return payload


@app.post("/nodes")
def create_node(payload: NodeCreateRequest, request: Request) -> dict:
    node = get_graph(request).create_or_get_node(payload.label)
    return {
        "id": node.id,
        "label": node.label,
        "created": node.created,
        "last_accessed": node.last_accessed,
        "access_count": node.access_count,
    }


@app.get("/nodes/{label}/exists")
def node_exists(label: str, request: Request) -> dict:
    return {"exists": get_graph(request).node_exists(label)}


@app.post("/edges")
def create_edge(payload: EdgeCreateRequest, request: Request) -> dict:
    edge = get_graph(request).create_edge(
        source_label=payload.source,
        target_label=payload.target,
        edge_type=payload.type,
        strength=payload.strength,
    )
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "type": edge.type.value,
        "strength": edge.strength,
    }


@app.get("/edges/{edge_id}")
def get_edge(edge_id: str, request: Request) -> dict:
    edge = get_graph(request).get_edge_by_id(edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge not found")
    return {
        "id": edge.id,
        "source": edge.source,
        "target": edge.target,
        "type": edge.type.value,
        "strength": edge.strength,
        "recall_count": edge.recall_count,
    }


@app.post("/edges/{edge_id}/strengthen")
def strengthen_edge(edge_id: str, request: Request) -> dict:
    edge = get_graph(request).strengthen_edge(edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"id": edge.id, "strength": edge.strength, "recall_count": edge.recall_count}


@app.post("/maintenance/decay")
def run_decay_once(request: Request) -> dict:
    decayed = get_graph(request).decay_all_edges()
    return {"decayed_edges": decayed}


@app.post("/bootstrap/default")
def bootstrap_default(request: Request) -> dict:
    created = get_graph(request).bootstrap_default()
    return {"created_relations": created}


@app.get("/nodes/{label}/neighbors")
def get_neighbors(label: str, request: Request) -> dict:
    edges = get_graph(request).get_neighbors(label)
    return {
        "count": len(edges),
        "edges": [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.type.value,
                "strength": edge.strength,
            }
            for edge in edges
        ],
    }


@app.get("/graph/hubs")
def graph_hubs(
    request: Request,
    limit: int = 20,
    min_total_degree: int = 2,
    min_edge_type_diversity: int = 1,
) -> dict:
    safe_limit = max(1, min(200, int(limit)))
    safe_total = max(1, min(1000, int(min_total_degree)))
    safe_types = max(1, min(10, int(min_edge_type_diversity)))
    hubs = get_graph(request).detect_hubs(
        limit=safe_limit,
        min_total_degree=safe_total,
        min_edge_type_diversity=safe_types,
    )
    return {
        "count": len(hubs),
        "items": [
            {
                "node_id": hub.node_id,
                "label": hub.node_label,
                "in_degree": hub.in_degree,
                "out_degree": hub.out_degree,
                "total_degree": hub.total_degree,
                "unique_neighbors": hub.unique_neighbors,
                "edge_type_diversity": hub.edge_type_diversity,
                "access_count": hub.access_count,
                "hub_score": hub.hub_score,
            }
            for hub in hubs
        ],
    }


@app.get("/graph/summary")
def graph_summary(
    request: Request,
    scope: str = "main",
    user_id: str = "guest",
    node_limit: int = 50,
    edge_limit: int = 120,
    min_strength: float = 0.0,
) -> dict:
    selected_scope = scope.strip().lower()
    if selected_scope not in {"main", "personal"}:
        selected_scope = "main"
    safe_node_limit = max(1, min(500, int(node_limit)))
    safe_edge_limit = max(1, min(2000, int(edge_limit)))
    safe_strength = max(0.0, min(1.0, float(min_strength)))

    graph = get_graph_for_scope(request, scope=selected_scope, user_id=user_id)
    nodes = graph.list_nodes(limit=safe_node_limit)
    edges = graph.list_edges(limit=safe_edge_limit, min_strength=safe_strength, sort_by="recent")
    node_ids = {node.id for node in nodes}
    for edge in edges:
        node_ids.add(edge.source)
        node_ids.add(edge.target)

    node_map = {}
    for node_id in node_ids:
        node = graph.store.get_node(node_id)
        if node is None:
            continue
        node_map[node_id] = node

    relation_text = {
        "CAUSES": "causes",
        "CORRELATES": "is associated with",
        "IS_A": "is a type of",
        "TEMPORAL": "usually happens before",
        "INFERRED": "is likely related to",
    }

    edge_items = []
    for edge in edges:
        source_label = graph.get_node_label(edge.source)
        target_label = graph.get_node_label(edge.target)
        relation = relation_text.get(edge.type.value, "is related to")
        description = (
            f"{source_label} {relation} {target_label}. "
            f"Type={edge.type.value}, strength={edge.strength:.3f}, recalls={edge.recall_count}."
        )
        edge_items.append(
            {
                "id": edge.id,
                "source_id": edge.source,
                "target_id": edge.target,
                "source_label": source_label,
                "target_label": target_label,
                "type": edge.type.value,
                "relation_text": relation,
                "strength": edge.strength,
                "recall_count": edge.recall_count,
                "created": edge.created,
                "last_activated": edge.last_activated,
                "description": description,
            }
        )

    outgoing_index: dict[str, list[dict]] = {}
    incoming_index: dict[str, list[dict]] = {}
    for item in edge_items:
        outgoing_index.setdefault(item["source_id"], []).append(item)
        incoming_index.setdefault(item["target_id"], []).append(item)

    node_items = [
        {
            "id": node.id,
            "label": node.label,
            "access_count": node.access_count,
            "created": node.created,
            "last_accessed": node.last_accessed,
            "description": _describe_node_for_summary(
                node_label=node.label,
                outgoing=outgoing_index.get(node.id, []),
                incoming=incoming_index.get(node.id, []),
            ),
        }
        for node in sorted(node_map.values(), key=lambda item: (-item.access_count, item.label))
    ]

    return {
        "scope": selected_scope,
        "user_id": sanitize_user_id(user_id),
        "store": graph.store_kind,
        "stats": {
            "total_nodes": graph.count_nodes(),
            "total_edges": graph.count_edges(),
            "returned_nodes": len(node_items),
            "returned_edges": len(edge_items),
            "min_strength": safe_strength,
        },
        "nodes": node_items,
        "edges": edge_items,
    }


@app.post("/reasoning/paths")
def reasoning_paths(payload: PathQueryRequest, request: Request) -> dict:
    paths = get_graph(request).find_paths(
        source_label=payload.source,
        target_label=payload.target,
        max_hops=payload.max_hops,
        max_paths=payload.max_paths,
        goal_relevance=payload.goal_relevance,
    )
    return {
        "count": len(paths),
        "paths": [
            {
                "node_labels": path.node_labels,
                "hops": path.hops,
                "edge_types": [edge_type.value for edge_type in path.edge_types],
                "edge_strengths": path.edge_strengths,
                "mean_strength": path.mean_strength,
                "score": path.score,
            }
            for path in paths
        ],
    }


@app.get("/reasoning/analogies/{label}")
def reasoning_analogies(
    label: str,
    request: Request,
    limit: int = 10,
    min_shared_neighbors: int = 2,
) -> dict:
    safe_limit = max(1, min(100, int(limit)))
    safe_shared = max(1, min(20, int(min_shared_neighbors)))
    items = get_graph(request).find_analogy_candidates(
        label,
        limit=safe_limit,
        min_shared_neighbors=safe_shared,
    )
    return {
        "source": label.strip().lower(),
        "count": len(items),
        "items": [
            {
                "candidate": item.candidate_label,
                "shared_neighbors": item.shared_neighbors,
                "shared_count": item.shared_count,
                "jaccard": item.jaccard,
                "score": item.score,
            }
            for item in items
        ],
    }


@app.post("/reasoning/consensus")
def reasoning_consensus(payload: ConsensusRequest, request: Request) -> dict:
    result = get_graph(request).path_consensus(
        source_label=payload.source,
        target_label=payload.target,
        max_hops=payload.max_hops,
        max_paths=payload.max_paths,
        cause_threshold=payload.cause_threshold,
        auto_upgrade=payload.auto_upgrade,
    )
    return {
        "source": result.source_label,
        "target": result.target_label,
        "path_count": result.path_count,
        "inferred_type": result.inferred_type.value,
        "upgraded": result.upgraded,
    }


@app.post("/reasoning/contradiction")
def reasoning_contradiction(payload: ContradictionRequest, request: Request) -> dict:
    result = get_graph(request).contradiction_vote(
        source_label=payload.source,
        positive_target=payload.positive_target,
        negative_target=payload.negative_target,
        max_hops=payload.max_hops,
        max_paths=payload.max_paths,
        weaken_factor=payload.weaken_factor,
    )
    return {
        "source": result.source_label,
        "positive_target": result.positive_target,
        "negative_target": result.negative_target,
        "positive_paths": result.positive_paths,
        "negative_paths": result.negative_paths,
        "verdict": result.verdict,
        "confidence": result.confidence,
        "minority_edge_weakened": result.minority_edge_weakened,
    }


@app.post("/query")
def query(payload: QueryRequest, request: Request) -> dict:
    user_id = sanitize_user_id(payload.user_id)
    _ = get_graph(request)
    rewriter = get_query_rewriter(request)
    rewrite = rewriter.rewrite(payload.text)
    rewritten_text = rewrite.rewritten_text
    scope_decision = decide_scope(rewritten_text, payload.scope)
    selected_scope = scope_decision.selected_scope
    mode_decision = decide_query_mode(rewritten_text, is_personal_scope=(selected_scope == "personal"))
    benefits_main_graph = scope_decision.benefits_main_graph and (not mode_decision.disable_graph_learning)

    user_state = get_user_state(request)
    _ = user_state.ensure_user(user_id)
    quota = user_state.consume_query(user_id)
    if not quota["allowed"]:
        raise HTTPException(status_code=429, detail="Query limit reached. Add credits by contributing new main-graph knowledge.")
    profile = user_state.get_user(user_id)

    pipeline = get_pipeline_for_scope(request, scope=selected_scope, user_id=user_id)

    result = pipeline.run(
        rewritten_text,
        max_hops=payload.max_hops,
        max_paths=payload.max_paths,
        allow_learning=not mode_decision.disable_graph_learning,
    )

    if payload.domain.strip().lower() == "auto":
        inferred_domain = detect_domain(text=rewritten_text, tokens=rewritten_text.lower().split())
    else:
        inferred_domain = normalize_domain(payload.domain)

    intent_step = next((step for step in result.steps if step.startswith("intent:")), "intent:unknown")
    intent_kind = intent_step.split(":", 1)[1] if ":" in intent_step else "unknown"

    llm = get_llm_refiner(request)
    llm_policy = request.app.state.settings.llm_policy
    llm_mode = "skip"
    llm_prefers_direct = mode_decision.prefer_direct_llm or intent_kind == "unknown" or (
        result.confidence < 0.08 and len(result.node_path) <= 1
    )
    llm_result = RefineResult(
        answer=result.answer,
        used=False,
        backend=llm.backend,
        model=llm.model,
        error=None,
        total_duration_ms=None,
    )

    if mode_decision.mode == "realtime":
        realtime = fetch_realtime_answer(rewritten_text)
        if realtime is not None:
            answer_text, source_name = realtime
            llm_mode = "web"
            llm_result = RefineResult(
                answer=answer_text,
                used=False,
                backend="web",
                model=source_name,
                error=None,
                total_duration_ms=None,
            )

    if llm_mode != "web" and llm.backend == "ollama":
        if llm_policy == "always":
            if llm_prefers_direct:
                llm_mode = "direct"
                llm_result = llm.answer_general(question=rewritten_text, domain=inferred_domain)
            else:
                llm_mode = "refine"
                llm_result = llm.refine_answer(
                    question=rewritten_text,
                    base_answer=result.answer,
                    node_path=result.node_path,
                    confidence=result.confidence,
                    scope=selected_scope,
                    domain=inferred_domain,
                    used_fallback=result.used_fallback,
                )
        elif llm_policy == "unknown_only":
            if llm_prefers_direct:
                llm_mode = "direct"
                llm_result = llm.answer_general(question=rewritten_text, domain=inferred_domain)
        else:
            # smart policy: direct-answer unknowns, refine only weak/learned graph answers.
            if llm_prefers_direct:
                llm_mode = "direct"
                llm_result = llm.answer_general(question=rewritten_text, domain=inferred_domain)
            elif result.used_fallback or result.confidence < 0.45:
                llm_mode = "refine"
                llm_result = llm.refine_answer(
                    question=rewritten_text,
                    base_answer=result.answer,
                    node_path=result.node_path,
                    confidence=result.confidence,
                    scope=selected_scope,
                    domain=inferred_domain,
                    used_fallback=result.used_fallback,
                )

    if llm_mode == "skip" and intent_kind == "unknown":
        troubleshooting = fetch_troubleshooting_answer(rewritten_text)
        if troubleshooting is not None:
            answer_text, source_name = troubleshooting
            llm_mode = "web"
            llm_result = RefineResult(
                answer=answer_text,
                used=False,
                backend="web",
                model=source_name,
                error=None,
                total_duration_ms=None,
            )

    final_answer = llm_result.answer.strip() if llm_result.answer.strip() else result.answer

    contribution = {
        "awarded_credits": 0,
        "credit_balance": profile.credit_balance,
        "main_nodes_contributed": profile.main_nodes_contributed,
        "domain": inferred_domain,
        "domain_multiplier": credit_multiplier(inferred_domain),
        "domain_nodes_contributed": profile.domain_nodes_contributed.get(inferred_domain, 0),
        "domain_credits_earned": profile.domain_credits_earned.get(inferred_domain, 0),
    }
    if selected_scope == "main" and benefits_main_graph and result.new_nodes_created > 0:
        contribution = user_state.award_main_graph_contribution(
            user_id,
            new_nodes_created=result.new_nodes_created,
            domain=inferred_domain,
        )
        profile = user_state.get_user(user_id)

    record = get_conversation_store(request).append(
        raw_text=payload.text,
        node_path=result.node_path,
        frozen_snapshot=final_answer,
        user_id=user_id,
        scope=selected_scope,
        domain=inferred_domain,
        intent=intent_kind,
        benefits_main_graph=benefits_main_graph,
        new_nodes_created=result.new_nodes_created,
        created_edges=result.created_edges,
        credits_awarded=contribution["awarded_credits"],
        llm_used=llm_result.used,
        used_fallback=result.used_fallback,
        confidence=result.confidence,
    )
    # Reinforce typo corrections only after a meaningful answer confidence.
    rewriter.reinforce(rewrite, reward=result.confidence)

    # Log metrics
    metrics = get_metrics_store(request)
    metrics.log_metric(
        fallback=result.used_fallback,
        shortcut=result.shortcut_applied,
        domain=inferred_domain
    )

    get_encoder_training_store(request).append(
        raw_text=rewritten_text,
        tokens=rewritten_text.split(),
        answer=final_answer,
        scope=selected_scope,
        domain=inferred_domain,
        intent=intent_kind,
        used_fallback=result.used_fallback,
        created_edges=result.created_edges,
        confidence=result.confidence,
        node_path=result.node_path,
        steps=result.steps,
        backend=result.encoder_backend,
    )
    return {
        "input_text": payload.text,
        "rewritten_text": rewritten_text,
        "rewrite_applied": rewrite.changed,
        "rewrite_confidence": rewrite.confidence,
        "rewrite_corrections": [
            {"from": item.source, "to": item.target, "score": item.score}
            for item in rewrite.corrections
        ],
        "answer": final_answer,
        "source": result.source,
        "target": result.target,
        "used_fallback": result.used_fallback,
        "created_edges": result.created_edges,
        "confidence": result.confidence,
        "node_path": result.node_path,
        "steps": result.steps,
        "encoder_backend": result.encoder_backend,
        "decoder_backend": getattr(pipeline.decoder, "backend", "unknown"),
        "llm_backend": llm_result.backend,
        "llm_model": llm_result.model,
        "llm_used": llm_result.used,
        "llm_error": llm_result.error,
        "llm_duration_ms": llm_result.total_duration_ms,
        "llm_mode": llm_mode,
        "llm_policy": llm_policy,
        "activation_ranges": result.activation_ranges,
        "active_dims": result.active_dims,
        "shortcut_applied": result.shortcut_applied,
        "expansion_node_id": result.expansion_node_id,
        "new_nodes_created": result.new_nodes_created,
        "user": {
            "user_id": profile.user_id,
            "tier": profile.tier,
            "daily_quota": profile.daily_quota,
            "remaining_daily": quota["remaining_daily"],
            "credit_balance": contribution["credit_balance"],
            "main_nodes_contributed": contribution["main_nodes_contributed"],
            "domain_nodes_contributed": contribution["domain_nodes_contributed"],
            "domain_credits_earned": contribution["domain_credits_earned"],
        },
        "credits_awarded": contribution["awarded_credits"],
        "domain": contribution["domain"],
        "domain_multiplier": contribution["domain_multiplier"],
        "scope": selected_scope,
        "scope_requested": scope_decision.requested_scope,
        "scope_reason": scope_decision.reason,
        "benefits_main_graph": benefits_main_graph,
        "query_mode": mode_decision.mode,
        "query_mode_reason": mode_decision.reason,
        "history_record_id": record.id,
        "stored_at": record.timestamp,
    }


@app.get("/encoder/training/recent")
def encoder_training_recent(request: Request, limit: int = 20) -> dict:
    safe_limit = max(1, min(200, int(limit)))
    items = get_encoder_training_store(request).recent(limit=safe_limit)
    return {"count": len(items), "items": items}


@app.post("/encoder/train")
def encoder_train(payload: EncoderTrainRequest, request: Request, user_id: str = "guest", scope: str = "main") -> dict:
    pipeline = get_pipeline_for_scope(request, scope=scope, user_id=user_id)
    encoder = pipeline.encoder
    train_fn = getattr(encoder, "train_from_records", None)
    if train_fn is None:
        raise HTTPException(status_code=400, detail="Current encoder backend is not trainable. Set PARAGI_ENCODER_BACKEND=own.")

    training_store = get_encoder_training_store(request)
    summary = train_fn(
        training_store.path,
        max_records=payload.max_records,
        min_confidence=payload.min_confidence,
        min_token_occurrences=payload.min_token_occurrences,
    )
    return {
        "ok": True,
        "scope": scope,
        "user_id": user_id,
        "encoder_backend": getattr(encoder, "_backend", "unknown"),
        "training_data_path": str(training_store.path),
        "summary": summary,
    }


@app.post("/decoder/train")
def decoder_train(payload: DecoderTrainRequest, request: Request) -> dict:
    pipeline = get_pipeline(request)
    decoder = pipeline.decoder
    train_fn = getattr(decoder, "train_from_records", None)
    if train_fn is None:
        raise HTTPException(status_code=400, detail="Current decoder backend is not trainable. Set PARAGI_DECODER_BACKEND=own.")

    training_store = get_encoder_training_store(request)
    summary = train_fn(
        training_store.path,
        max_records=payload.max_records,
        min_confidence=payload.min_confidence,
        min_samples=payload.min_samples,
    )
    return {
        "ok": True,
        "decoder_backend": getattr(decoder, "backend", "unknown"),
        "training_data_path": str(training_store.path),
        "summary": summary,
    }


@app.get("/query/history")
def query_history(request: Request, limit: int = 20) -> dict:
    safe_limit = max(1, min(100, int(limit)))
    items = get_conversation_store(request).recent(limit=safe_limit)
    return {
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "raw_text": item.raw_text,
                "user_id": item.user_id,
                "scope": item.scope,
                "domain": item.domain,
                "node_path": item.node_path,
                "frozen_snapshot": item.frozen_snapshot,
                "used_fallback": item.used_fallback,
                "confidence": item.confidence,
                "timestamp": item.timestamp,
                "intent": item.intent,
                "benefits_main_graph": item.benefits_main_graph,
                "new_nodes_created": item.new_nodes_created,
                "created_edges": item.created_edges,
                "credits_awarded": item.credits_awarded,
                "llm_used": item.llm_used,
            }
            for item in items
        ],
    }


@app.get("/query/history/user/{user_id}")
def query_history_by_user(user_id: str, request: Request, limit: int = 50, scope: str = "all") -> dict:
    safe_user = sanitize_user_id(user_id)
    safe_limit = max(1, min(500, int(limit)))
    selected_scope = scope.strip().lower()
    items = get_conversation_store(request).by_user(safe_user, limit=safe_limit)
    if selected_scope in {"main", "personal"}:
        items = [item for item in items if item.scope == selected_scope]
    else:
        selected_scope = "all"

    return {
        "user_id": safe_user,
        "scope": selected_scope,
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "raw_text": item.raw_text,
                "user_id": item.user_id,
                "scope": item.scope,
                "domain": item.domain,
                "node_path": item.node_path,
                "frozen_snapshot": item.frozen_snapshot,
                "used_fallback": item.used_fallback,
                "confidence": item.confidence,
                "timestamp": item.timestamp,
                "intent": item.intent,
                "benefits_main_graph": item.benefits_main_graph,
                "new_nodes_created": item.new_nodes_created,
                "created_edges": item.created_edges,
                "credits_awarded": item.credits_awarded,
                "llm_used": item.llm_used,
            }
            for item in items
        ],
    }


@app.get("/query/history/{record_id}/evolution")
def query_history_evolution(record_id: str, request: Request, max_hops: int = 7, max_paths: int = 64) -> dict:
    record = get_conversation_store(request).get_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record not found")

    safe_hops = max(1, min(12, int(max_hops)))
    safe_paths = max(1, min(512, int(max_paths)))
    pipeline = get_pipeline_for_scope(request, scope=record.scope, user_id=record.user_id)
    rewrite = get_query_rewriter(request).rewrite(record.raw_text)
    replay = pipeline.run(rewrite.rewritten_text, max_hops=safe_hops, max_paths=safe_paths, allow_learning=False)
    intent_step = next((step for step in replay.steps if step.startswith("intent:")), "intent:unknown")
    intent_kind = intent_step.split(":", 1)[1] if ":" in intent_step else "unknown"
    llm = get_llm_refiner(request)
    llm_policy = request.app.state.settings.llm_policy
    llm_mode = "skip"
    llm_prefers_direct = intent_kind == "unknown" or (
        replay.confidence < 0.08 and len(replay.node_path) <= 1
    )
    llm_result = RefineResult(
        answer=replay.answer,
        used=False,
        backend=llm.backend,
        model=llm.model,
        error=None,
        total_duration_ms=None,
    )

    if llm.backend == "ollama":
        if llm_policy == "always":
            if llm_prefers_direct:
                llm_mode = "direct"
                llm_result = llm.answer_general(question=rewrite.rewritten_text, domain=record.domain)
            else:
                llm_mode = "refine"
                llm_result = llm.refine_answer(
                    question=rewrite.rewritten_text,
                    base_answer=replay.answer,
                    node_path=replay.node_path,
                    confidence=replay.confidence,
                    scope=record.scope,
                    domain=record.domain,
                    used_fallback=replay.used_fallback,
                )
        elif llm_policy == "unknown_only":
            if llm_prefers_direct:
                llm_mode = "direct"
                llm_result = llm.answer_general(question=rewrite.rewritten_text, domain=record.domain)
        else:
            if llm_prefers_direct:
                llm_mode = "direct"
                llm_result = llm.answer_general(question=rewrite.rewritten_text, domain=record.domain)
            elif replay.used_fallback or replay.confidence < 0.45:
                llm_mode = "refine"
                llm_result = llm.refine_answer(
                    question=rewrite.rewritten_text,
                    base_answer=replay.answer,
                    node_path=replay.node_path,
                    confidence=replay.confidence,
                    scope=record.scope,
                    domain=record.domain,
                    used_fallback=replay.used_fallback,
                )
    replay_answer = llm_result.answer.strip() if llm_result.answer.strip() else replay.answer
    changed = replay_answer.strip() != record.frozen_snapshot.strip()

    return {
        "record_id": record.id,
        "raw_text": record.raw_text,
        "user_id": record.user_id,
        "scope": record.scope,
        "domain": record.domain,
        "stored_at": record.timestamp,
        "frozen_snapshot": record.frozen_snapshot,
        "updated_answer": replay_answer,
        "changed": changed,
        "original_confidence": record.confidence,
        "updated_confidence": replay.confidence,
        "confidence_delta": replay.confidence - record.confidence,
        "used_fallback_now": replay.used_fallback,
        "node_path_then": record.node_path,
        "node_path_now": replay.node_path,
        "steps_now": replay.steps,
        "rewritten_text_now": rewrite.rewritten_text,
        "rewrite_applied_now": rewrite.changed,
        "llm_backend_now": llm_result.backend,
        "llm_model_now": llm_result.model,
        "llm_used_now": llm_result.used,
        "llm_error_now": llm_result.error,
        "llm_mode_now": llm_mode,
        "llm_policy_now": llm_policy,
    }


@app.get("/expansion/nodes")
def expansion_nodes(request: Request, limit: int = 20) -> dict:
    safe_limit = max(1, min(100, int(limit)))
    items = get_expansion_queue(request).list_recent(limit=safe_limit)
    return {
        "count": len(items),
        "items": [
            {
                "id": node.id,
                "query_text": node.query_text,
                "source": node.source,
                "target": node.target,
                "status": node.status,
                "attempts": node.attempts,
                "resolved_edges": node.resolved_edges,
                "provenance": node.provenance,
                "last_error": node.last_error,
                "created_at": node.created_at,
                "updated_at": node.updated_at,
            }
            for node in items
        ],
    }


@app.post("/expansion/resolve")
def expansion_resolve(request: Request, max_items: int = 3) -> dict:
    safe_items = max(1, min(20, int(max_items)))
    resolved = get_expansion_resolver(request).resolve_pending(max_items=safe_items)
    return {"resolved": resolved}


@app.post("/auth/register")
def auth_register(payload: AuthRegisterRequest, request: Request) -> dict:
    auth = get_auth_store(request)
    user_state = get_user_state(request)
    try:
        created = auth.register(payload.user_id, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    profile = user_state.register_user(created.user_id, tier=payload.tier)
    session = auth.login(created.user_id, payload.password)
    if session is None:
        raise HTTPException(status_code=500, detail="Failed to create login session.")
    return {
        "user_id": profile.user_id,
        "tier": profile.tier,
        "token": session.token,
        "session_expires_at": session.expires_at,
    }


@app.post("/auth/login")
def auth_login(payload: AuthLoginRequest, request: Request) -> dict:
    auth = get_auth_store(request)
    user_state = get_user_state(request)
    session = auth.login(payload.user_id, payload.password)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid user ID or password.")
    profile = user_state.get_user(session.user_id)
    return {
        "user_id": profile.user_id,
        "tier": profile.tier,
        "token": session.token,
        "session_expires_at": session.expires_at,
    }


@app.get("/auth/session")
def auth_session(token: str, request: Request) -> dict:
    auth = get_auth_store(request)
    user_state = get_user_state(request)
    session = auth.get_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    profile = user_state.get_user(session.user_id)
    return {
        "user_id": profile.user_id,
        "tier": profile.tier,
        "token": session.token,
        "session_expires_at": session.expires_at,
        "last_seen_at": session.last_seen_at,
    }


@app.post("/auth/logout")
def auth_logout(payload: AuthLogoutRequest, request: Request) -> dict:
    removed = get_auth_store(request).logout(payload.token)
    return {"ok": removed}


@app.post("/auth/google")
def auth_google(payload: AuthGoogleRequest, request: Request) -> dict:
    client_id = request.app.state.settings.google_client_id
    if not client_id:
        raise HTTPException(status_code=500, detail="Google authentication is not configured.")
    try:
        idinfo = id_token.verify_oauth2_token(payload.credential, google_requests.Request(), client_id)
        email = idinfo.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google token does not contain an email address.")
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(exc)}")
    
    auth = get_auth_store(request)
    session = auth.google_login(email)
    return {
        "ok": True,
        "token": session.token,
        "user_id": session.user_id,
        "tier": "free",
        "session_expires_at": session.expires_at,
    }


@app.post("/users/register")
def users_register(payload: UserRegisterRequest, request: Request) -> dict:
    profile = get_user_state(request).register_user(payload.user_id, tier=payload.tier)
    return {
        "user_id": profile.user_id,
        "tier": profile.tier,
        "daily_quota": profile.daily_quota,
        "credit_balance": profile.credit_balance,
    }


@app.get("/users/{user_id}")
def users_get(user_id: str, request: Request) -> dict:
    profile = get_user_state(request).get_user(user_id)
    return {
        "user_id": profile.user_id,
        "tier": profile.tier,
        "daily_quota": profile.daily_quota,
        "query_used_today": profile.query_used_today,
        "credit_balance": profile.credit_balance,
        "credits_earned_total": profile.credits_earned_total,
        "main_nodes_contributed": profile.main_nodes_contributed,
        "domain_nodes_contributed": profile.domain_nodes_contributed,
        "domain_credits_earned": profile.domain_credits_earned,
        "last_reset_date": profile.last_reset_date,
    }


@app.get("/users/{user_id}/impact")
def users_impact(user_id: str, request: Request, limit: int = 50) -> dict:
    safe_user = sanitize_user_id(user_id)
    safe_limit = max(1, min(500, int(limit)))
    # Pull a deeper slice for summary and a shorter slice for UI rendering.
    records = get_conversation_store(request).by_user(safe_user, limit=2000)

    total_records = len(records)
    personal_records = [item for item in records if item.scope == "personal"]
    personal_memories = []
    for item in personal_records:
        if len(item.node_path) >= 2 and item.node_path[0] == "self":
            personal_memories.append(
                {
                    "attribute_value": item.node_path[1],
                    "stored_at": item.timestamp,
                    "confidence": item.confidence,
                }
            )
    personal_memories.sort(key=lambda row: row["stored_at"], reverse=True)

    impactful = [
        item
        for item in records
        if (
            item.benefits_main_graph
            or item.new_nodes_created > 0
            or item.created_edges > 0
            or item.credits_awarded > 0
        )
    ]
    nodes_added = sum(item.new_nodes_created for item in impactful if item.scope == "main")
    edges_added = sum(item.created_edges for item in impactful if item.scope == "main")
    credits_earned = sum(item.credits_awarded for item in impactful)
    personal_impact_records = sum(1 for item in impactful if item.scope == "personal")

    recent_items = []
    for item in impactful[:safe_limit]:
        recent_items.append(
            {
                "record_id": item.id,
                "query": item.raw_text,
                "intent": item.intent,
                "domain": item.domain,
                "scope": item.scope,
                "new_nodes_created": item.new_nodes_created,
                "created_edges": item.created_edges,
                "credits_awarded": item.credits_awarded,
                "node_path": item.node_path,
                "confidence": item.confidence,
                "benefits_main_graph": item.benefits_main_graph,
                "stored_at": item.timestamp,
            }
        )

    return {
        "user_id": safe_user,
        "summary": {
            "total_records": total_records,
            "personal_records": len(personal_records),
            "main_impact_records": len(impactful),
            "personal_impact_records": personal_impact_records,
            "nodes_added_to_main_graph": nodes_added,
            "edges_added_to_main_graph": edges_added,
            "credits_earned_from_impact": credits_earned,
        },
        "personal_memory": {
            "count": len(personal_memories),
            "items": personal_memories[:safe_limit],
        },
        "main_graph_impact": {
            "count": len(impactful),
            "items": recent_items,
        },
    }


@app.get("/leaderboard/contributors")
def leaderboard_contributors(request: Request, limit: int = 20) -> dict:
    items = get_user_state(request).leaderboard(limit=limit)
    return {
        "count": len(items),
        "items": [
            {
                "rank": idx + 1,
                "user_id": profile.user_id,
                "tier": profile.tier,
                "main_nodes_contributed": profile.main_nodes_contributed,
                "credits_earned_total": profile.credits_earned_total,
                "top_domain": max(profile.domain_nodes_contributed, key=profile.domain_nodes_contributed.get, default="general"),
            }
            for idx, profile in enumerate(items)
        ],
    }


@app.get("/leaderboard/contributors/{domain}")
def leaderboard_contributors_domain(domain: str, request: Request, limit: int = 20) -> dict:
    domain_name = normalize_domain(domain)
    items = get_user_state(request).leaderboard_by_domain(domain_name, limit=limit)
    return {
        "domain": domain_name,
        "count": len(items),
        "items": [
            {
                "rank": idx + 1,
                "user_id": profile.user_id,
                "tier": profile.tier,
                "domain_nodes_contributed": profile.domain_nodes_contributed.get(domain_name, 0),
                "domain_credits_earned": profile.domain_credits_earned.get(domain_name, 0),
            }
            for idx, profile in enumerate(items)
        ],
    }


@app.get("/domains")
def domains_catalog() -> dict:
    domains = available_domains()
    return {
        "count": len(domains),
        "domains": [
            {"name": domain, "credit_multiplier": credit_multiplier(domain)}
            for domain in domains
        ],
    }


@app.get("/leaderboard/domains")
def leaderboard_domains(request: Request) -> dict:
    items = get_user_state(request).domain_summary()
    return {
        "count": len(items),
        "items": items,
    }


@app.post("/crawl")
async def trigger_crawl(
    payload: CrawlRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    token: str = Header(...)
) -> dict:
    auth = get_auth_store(request)
    session = auth.get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    user_state = get_user_state(request)
    profile = user_state.get_user(session.user_id)
    if profile.tier != "contributor":
        raise HTTPException(status_code=403, detail="Contributor tier required")

    crawler = get_crawler(request)
    background_tasks.add_task(crawler.crawl_query, payload.url)

    return {"ok": True, "message": "Crawl task queued"}


@app.get("/crawl/status")
def crawl_status(request: Request) -> dict:
    crawler = get_crawler(request)
    return {
        "queue_size": crawler.queue_size,
        "pages_crawled": crawler.pages_crawled
    }
