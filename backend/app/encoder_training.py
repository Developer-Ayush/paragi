from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List


class EncoderTrainingStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def append(
        self,
        *,
        raw_text: str,
        tokens: List[str],
        answer: str,
        scope: str,
        domain: str,
        intent: str,
        used_fallback: bool,
        created_edges: int,
        confidence: float,
        node_path: List[str],
        steps: List[str],
        backend: str,
    ) -> None:
        sample = {
            "timestamp": time.time(),
            "raw_text": raw_text,
            "tokens": list(tokens),
            "answer": answer,
            "scope": scope,
            "domain": domain,
            "intent": intent,
            "used_fallback": bool(used_fallback),
            "created_edges": int(created_edges),
            "confidence": float(confidence),
            "node_path": list(node_path),
            "steps": list(steps),
            "backend": backend,
        }
        line = json.dumps(sample, ensure_ascii=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fp:
                fp.write(line + "\n")

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        if not self.path.exists():
            return []
        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        rows: List[Dict[str, Any]] = []
        for line in reversed(lines[-limit:]):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows
