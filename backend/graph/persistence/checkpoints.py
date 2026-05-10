"""graph/persistence/checkpoints.py — Checkpoint save/restore for graph state."""
from __future__ import annotations

import json
import time
from pathlib import Path

from core.logger import get_logger

log = get_logger(__name__)


def save_checkpoint(graph_engine: object, checkpoint_dir: Path) -> Path:
    """Save a lightweight graph checkpoint (node/edge counts + timestamp)."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    meta = {
        "timestamp": ts,
        "node_count": graph_engine.count_nodes(),  # type: ignore
        "edge_count": graph_engine.count_edges(),  # type: ignore
        "store_kind": graph_engine.store_kind,     # type: ignore
    }
    path = checkpoint_dir / f"checkpoint_{ts}.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info(f"Checkpoint saved: {path}")
    return path


def list_checkpoints(checkpoint_dir: Path) -> list[Path]:
    """List all checkpoint files sorted newest-first."""
    if not checkpoint_dir.exists():
        return []
    return sorted(checkpoint_dir.glob("checkpoint_*.json"), reverse=True)
