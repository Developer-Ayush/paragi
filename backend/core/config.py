"""core/config.py — Settings for the Paragi cognitive runtime.

Ported from app/config.py with additions for the cognitive architecture.
All configuration is read from environment variables with sensible defaults.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # ── Paths ────────────────────────────────────────────────────────────
    data_dir: Path
    hdf5_path: Path
    bloom_path: Path
    query_history_path: Path
    metrics_path: Path
    expansion_queue_path: Path
    user_state_path: Path
    auth_users_path: Path
    auth_sessions_path: Path

    # ── Bloom filter ──────────────────────────────────────────────────────
    bloom_capacity: int
    bloom_error_rate: float

    # ── Edge lifecycle ────────────────────────────────────────────────────
    edge_decay_per_cycle: float
    edge_strength_floor: float
    edge_prune_threshold: float
    decay_interval_seconds: float
    expansion_interval_seconds: float

    # ── Storage backend ───────────────────────────────────────────────────
    prefer_hdf5: bool

    # ── Encoder ───────────────────────────────────────────────────────────
    encoder_backend: str           # own | fastembed | hash
    encoder_model_path: Path
    encoder_training_path: Path

    # ── Decoder ───────────────────────────────────────────────────────────
    decoder_backend: str           # own | temporary
    decoder_model_path: Path

    # ── Query rewriter ────────────────────────────────────────────────────
    query_rewriter_path: Path

    # ── LLM (semantic translation boundary only) ──────────────────────────
    llm_backend: str               # none | ollama | groq
    llm_model: str
    llm_base_url: str
    llm_timeout_seconds: float
    llm_temperature: float
    llm_max_tokens: int
    llm_seed: int
    llm_keep_alive: str
    llm_policy: str                # always | smart | unknown_only
    llm_api_key: str
    api_key: str
    api_key_required: bool

    # ── Auth ──────────────────────────────────────────────────────────────
    google_client_id: str

    # ── Cognition / memory ────────────────────────────────────────────────
    learning_confidence_threshold: float
    episodic_decay_hours: float
    realtime_ttl_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        # Determine data directory relative to backend root
        backend_root = Path(__file__).resolve().parents[1]
        data_dir = Path(os.getenv("PARAGI_DATA_DIR", str(backend_root / "data")))
        hdf5_path = Path(os.getenv("PARAGI_HDF5_PATH", str(data_dir / "memory.h5")))
        bloom_path = Path(os.getenv("PARAGI_BLOOM_PATH", str(data_dir / "nodes.bloom.json")))
        query_history_path = Path(os.getenv("PARAGI_QUERY_HISTORY_PATH", str(data_dir / "query_history.jsonl")))
        metrics_path = Path(os.getenv("PARAGI_METRICS_PATH", str(data_dir / "metrics.jsonl")))
        expansion_queue_path = Path(os.getenv("PARAGI_EXPANSION_QUEUE_PATH", str(data_dir / "expansion_queue.json")))
        user_state_path = Path(os.getenv("PARAGI_USER_STATE_PATH", str(data_dir / "users_state.json")))
        auth_users_path = Path(os.getenv("PARAGI_AUTH_USERS_PATH", str(data_dir / "auth_users.json")))
        auth_sessions_path = Path(os.getenv("PARAGI_AUTH_SESSIONS_PATH", str(data_dir / "auth_sessions.json")))
        encoder_model_path = Path(os.getenv("PARAGI_ENCODER_MODEL_PATH", str(data_dir / "encoder_model.json")))
        encoder_training_path = Path(os.getenv("PARAGI_ENCODER_TRAINING_PATH", str(data_dir / "encoder_training.jsonl")))
        decoder_model_path = Path(os.getenv("PARAGI_DECODER_MODEL_PATH", str(data_dir / "decoder_model.json")))
        query_rewriter_path = Path(os.getenv("PARAGI_QUERY_REWRITER_PATH", str(data_dir / "query_rewriter.json")))

        encoder_backend = os.getenv("PARAGI_ENCODER_BACKEND", "own").strip().lower()
        if encoder_backend not in {"own", "temporary", "hash", "fastembed"}:
            encoder_backend = "own"

        decoder_backend = os.getenv("PARAGI_DECODER_BACKEND", "own").strip().lower()
        if decoder_backend not in {"own", "temporary"}:
            decoder_backend = "own"

        llm_backend = os.getenv("PARAGI_LLM_BACKEND", "none").strip().lower()
        if llm_backend not in {"none", "ollama", "groq"}:
            llm_backend = "none"

        llm_model = os.getenv("PARAGI_LLM_MODEL", "gemma3:4b").strip() or "gemma3:4b"
        llm_base_url = os.getenv("PARAGI_LLM_BASE_URL", "http://127.0.0.1:11434").strip() or "http://127.0.0.1:11434"
        llm_timeout_seconds = float(os.getenv("PARAGI_LLM_TIMEOUT_SECONDS", "45"))
        llm_temperature = float(os.getenv("PARAGI_LLM_TEMPERATURE", "0.2"))
        llm_max_tokens = int(os.getenv("PARAGI_LLM_MAX_TOKENS", "220"))
        llm_seed = int(os.getenv("PARAGI_LLM_SEED", "42"))
        llm_keep_alive = os.getenv("PARAGI_LLM_KEEP_ALIVE", "30m").strip() or "30m"
        llm_policy = os.getenv("PARAGI_LLM_POLICY", "smart").strip().lower()
        if llm_policy not in {"always", "smart", "unknown_only"}:
            llm_policy = "smart"
        llm_api_key = (
            os.getenv("GROQ_API_KEY", "").strip()
            or os.getenv("PARAGI_LLM_API_KEY", "").strip()
        )
        google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        api_key = os.getenv("PARAGI_API_KEY", "").strip()
        api_key_required = bool(api_key)

        learning_confidence_threshold = float(os.getenv("PARAGI_LEARNING_THRESHOLD", "0.5"))
        episodic_decay_hours = float(os.getenv("PARAGI_EPISODIC_DECAY_HOURS", "24.0"))
        realtime_ttl_seconds = float(os.getenv("PARAGI_REALTIME_TTL_SECONDS", "3600.0"))

        settings = cls(
            data_dir=data_dir,
            hdf5_path=hdf5_path,
            bloom_path=bloom_path,
            query_history_path=query_history_path,
            metrics_path=metrics_path,
            expansion_queue_path=expansion_queue_path,
            user_state_path=user_state_path,
            auth_users_path=auth_users_path,
            auth_sessions_path=auth_sessions_path,
            bloom_capacity=int(os.getenv("PARAGI_BLOOM_CAPACITY", "1000000")),
            bloom_error_rate=float(os.getenv("PARAGI_BLOOM_ERROR_RATE", "0.001")),
            edge_decay_per_cycle=float(os.getenv("PARAGI_EDGE_DECAY_PER_CYCLE", "0.005")),
            edge_strength_floor=float(os.getenv("PARAGI_EDGE_STRENGTH_FLOOR", "0.001")),
            edge_prune_threshold=float(os.getenv("PARAGI_EDGE_PRUNE_THRESHOLD", "0.005")),
            decay_interval_seconds=float(os.getenv("PARAGI_DECAY_INTERVAL_SECONDS", "30")),
            expansion_interval_seconds=float(os.getenv("PARAGI_EXPANSION_INTERVAL_SECONDS", "30")),
            prefer_hdf5=os.getenv("PARAGI_PREFER_HDF5", "1") == "1",
            encoder_backend=encoder_backend,
            encoder_model_path=encoder_model_path,
            encoder_training_path=encoder_training_path,
            decoder_backend=decoder_backend,
            decoder_model_path=decoder_model_path,
            query_rewriter_path=query_rewriter_path,
            llm_backend=llm_backend,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            llm_timeout_seconds=llm_timeout_seconds,
            llm_temperature=llm_temperature,
            llm_max_tokens=llm_max_tokens,
            llm_seed=llm_seed,
            llm_keep_alive=llm_keep_alive,
            llm_policy=llm_policy,
            llm_api_key=llm_api_key,
            google_client_id=google_client_id,
            api_key=api_key,
            api_key_required=api_key_required,
            learning_confidence_threshold=learning_confidence_threshold,
            episodic_decay_hours=episodic_decay_hours,
            realtime_ttl_seconds=realtime_ttl_seconds,
        )
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        return settings
