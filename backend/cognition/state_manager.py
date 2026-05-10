"""cognition/state_manager.py — Per-user cognitive state.

Ported from app/user_state_store.py. Manages persistent user state.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class UserStateStore:
    """Thread-safe JSON-backed user state store."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(user_id, {}).get(key, default)

    def set(self, user_id: str, key: str, value: Any) -> None:
        with self._lock:
            if user_id not in self._data:
                self._data[user_id] = {}
            self._data[user_id][key] = value
            self._save()

    def get_user(self, user_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data.get(user_id, {}))

    def delete_user(self, user_id: str) -> None:
        with self._lock:
            self._data.pop(user_id, None)
            self._save()
