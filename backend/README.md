# Paragi Backend (Phase 5 Prototype)

This backend implements the first practical build blocks from your architecture plan:

- Node and edge storage
- Bloom filter existence checks
- Edge strengthening and decay with floor
- Seed bootstrap for initial typed knowledge
- Multi-hop traversal path reasoning
- Path consensus for causal upgrade
- Contradiction voting with confidence score
- Trainable own encoder/decoder backends with temporary fallback
- End-to-end query pipeline: text -> encode -> bloom check -> traversal -> decode
- Query record storage: raw text + node path + frozen snapshot
- Query classification + dynamic activation ranges (expand/collapse behavior)
- Expansion-node queue with background resolution loop
- Three-source connectors (ConceptNet, Semantic Scholar, Wikipedia)
- Two-graph model: shared main graph + per-user personal graph
- Contribution credit economy: new main-graph nodes award usage credits
- Domain-aware contribution scoring and credit multipliers
- Domain-specific contributor leaderboards
- API root at `/` (UI is served by Next.js frontend on `http://localhost:3000`)
- Minimal API for testing and integration

## Structure

- `app/models.py` node/edge models and IDs
- `app/bloom.py` Bloom filter + persistence
- `app/storage.py` HDF5 store and in-memory store
- `app/graph.py` graph engine operations
- `app/decay_worker.py` periodic decay background worker
- `app/query_pipeline.py` temporary encoder/decoder and query orchestration
- `app/query_control.py` query classification and activation profile
- `app/query_rewriter.py` typo-aware query normalization with persistent correction learning
- `app/expansion.py` expansion node queue and resolver
- `app/external_sources.py` external source connectors
- `app/expansion_worker.py` background expansion-node resolver
- `app/conversation_store.py` query history persistence
- `app/domain_policy.py` domain detection and credit multipliers
- `app/own_encoder.py` own 700-dim encoder + lightweight training loop
- `app/own_decoder.py` own natural-language decoder + lightweight calibration loop
- `app/encoder_training.py` encoder training sample recorder
- `app/user_state.py` user profiles, quotas, and credit ledger
- `app/personal_graphs.py` per-user private graph manager
- `app/main.py` FastAPI endpoints
- `frontend/chat.html` lightweight chat interface
- `tests/` unit tests

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run tests

```powershell
cd backend
python -m unittest discover -s tests -v
```

## Run API

```powershell
cd backend
uvicorn app.main:app --reload
```

## Key endpoints

- `GET /health`
- `POST /nodes` with `{ "label": "fire" }`
- `GET /nodes/{label}/exists`
- `POST /edges` with `{ "source": "fire", "target": "burn", "type": "CAUSES", "strength": 0.9 }`
- `POST /bootstrap/default`
- `POST /maintenance/decay`
- `POST /reasoning/paths`
- `GET /graph/hubs?limit=20&min_total_degree=2&min_edge_type_diversity=1`
- `GET /graph/summary?scope=main&user_id=alice&node_limit=50&edge_limit=120&min_strength=0.08`
- `GET /reasoning/analogies/{label}?limit=10&min_shared_neighbors=2`
- `POST /reasoning/consensus`
- `POST /reasoning/contradiction`
- `POST /query` with `{ "text": "does steam burn?", "user_id": "alice", "scope": "auto", "domain": "auto" }`
- `GET /llm/status`
- `GET /query/history?limit=20`
- `GET /query/history/user/{user_id}?limit=50&scope=all|main|personal`
- `GET /query/history/{record_id}/evolution` (replays stored query in no-learning mode to compare old vs current answer)
- `GET /encoder/training/recent?limit=20`
- `POST /encoder/train` with `{ "max_records": 50000, "min_confidence": 0.3, "min_token_occurrences": 2 }`
- `POST /decoder/train` with `{ "max_records": 50000, "min_confidence": 0.3, "min_samples": 20 }`
- `GET /expansion/nodes?limit=20`
- `POST /expansion/resolve?max_items=3`
- `POST /users/register` with `{ "user_id": "alice", "tier": "free" }`
- `POST /auth/register` with `{ "user_id": "alice", "password": "pass1234" }`
- `POST /auth/login` with `{ "user_id": "alice", "password": "pass1234" }`
- `GET /auth/session?token=...`
- `POST /auth/logout` with `{ "token": "..." }`
- `GET /users/{user_id}`
- `GET /users/{user_id}/impact?limit=50` (personal memory + main-graph impact summary)
- `GET /leaderboard/contributors?limit=20`
- `GET /leaderboard/contributors/{domain}?limit=20`
- `GET /leaderboard/domains`
- `GET /domains`
- `GET /` (API service info)

## Notes

- By default, the app prefers HDF5 when `h5py`/`numpy` are installed.
- If those dependencies are not available, it falls back to in-memory storage.
- Data files are stored in `backend/data/` unless overridden by environment variables.
- External connectors are best-effort; if network is unavailable, expansion nodes stay pending and retry later.
- Query `domain` can be `auto` (detected) or explicit (`general`, `medical`, `legal`, `physics`, `finance`, `technology`).
- Query `scope` can be `auto`, `main`, or `personal`. In `auto`, profile-like inputs route to personal memory and world-knowledge queries route to the main graph.
- Personal-memory pattern examples include `my nationality is ...` and `what is my nationality`; these stay in personal graph.
- Some personal queries can still be marked `benefits_main_graph=true` for impact tracking.
- Query text is typo-normalized before routing and reasoning (example: `what is my naem` -> `what is my name`).
- Query history items now include stable `id`, `user_id`, `scope`, and `domain` fields for reliable replay/evolution UX.
- Query history now also stores `intent`, `new_nodes_created`, `created_edges`, `credits_awarded`, and `benefits_main_graph`.
- Graph summary now includes rich hover fields:
  - `nodes[].description`
  - `edges[].relation_text`
  - `edges[].description`
- Encoder backend is controlled by `PARAGI_ENCODER_BACKEND` (`own`, `temporary`, `hash`, `fastembed`). Default is `own`.
- Encoder model and training data paths can be overridden via `PARAGI_ENCODER_MODEL_PATH` and `PARAGI_ENCODER_TRAINING_PATH`.
- Decoder backend is controlled by `PARAGI_DECODER_BACKEND` (`own`, `temporary`). Default is `own`.
- Decoder model path can be overridden via `PARAGI_DECODER_MODEL_PATH`.
- LLM answer refinement is controlled by `PARAGI_LLM_BACKEND` (`none`, `groq`). Default is `groq`.
- OpenRouter options: `PARAGI_LLM_MODEL` (default `google/gemini-2.0-flash-lite-preview-02-05:free`), `PARAGI_LLM_TIMEOUT_SECONDS`, `PARAGI_LLM_TEMPERATURE`, `PARAGI_LLM_MAX_TOKENS`, `PARAGI_LLM_API_KEY` (or `GROQ_API_KEY`).
- LLM routing policy: `PARAGI_LLM_POLICY` = `smart|always|unknown_only` (default `smart`).
- Query mode classifier marks realtime/open web-style questions and disables graph learning for those queries.
- Realtime mode examples: `who is ...`, `latest ...`, `current ...`, `today ...`; these do not create graph edges/nodes or award contribution credits.
- CORS is enabled for local Next.js frontend origins:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Default `PARAGI_LLM_TIMEOUT_SECONDS` is `45` to allow first model load.
- To avoid "fresh memory every run", keep persistent store enabled:
  - use default `PARAGI_PREFER_HDF5=1`
  - confirm `GET /health` returns `persistent_memory: true`
- Query rewriter persistence path can be overridden via `PARAGI_QUERY_REWRITER_PATH`.

## Use OpenRouter

```powershell
cd backend
$env:PARAGI_LLM_BACKEND="groq"
$env:PARAGI_LLM_MODEL="google/gemini-2.0-flash-lite-preview-02-05:free"
$env:PARAGI_LLM_API_KEY="your_openrouter_key"
$env:PARAGI_LLM_POLICY="smart"
uvicorn app.main:app --reload
```

Check runtime status:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/llm/status"
```
