from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List


LEGACY_CONTEXT_RE = re.compile(r"^\[(?P<user>[^|\]]+)\|(?P<scope>main|personal)\]\s*(?P<text>.*)$", re.IGNORECASE)
VALID_SCOPES = {"main", "personal"}


@dataclass(slots=True)
class QueryRecord:
    id: str
    raw_text: str
    user_id: str
    scope: str
    domain: str
    node_path: List[str]
    frozen_snapshot: str
    used_fallback: bool
    confidence: float
    timestamp: float
    intent: str = "unknown"
    benefits_main_graph: bool = False
    new_nodes_created: int = 0
    created_edges: int = 0
    credits_awarded: int = 0
    llm_used: bool = False


class ConversationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def append(
        self,
        raw_text: str,
        node_path: List[str],
        frozen_snapshot: str,
        *,
        user_id: str = "guest",
        scope: str = "main",
        domain: str = "general",
        intent: str = "unknown",
        benefits_main_graph: bool = False,
        new_nodes_created: int = 0,
        created_edges: int = 0,
        credits_awarded: int = 0,
        llm_used: bool = False,
        used_fallback: bool,
        confidence: float,
    ) -> QueryRecord:
        safe_scope = scope.strip().lower()
        if safe_scope not in VALID_SCOPES:
            safe_scope = "main"
        safe_user_id = user_id.strip() or "guest"
        safe_domain = domain.strip().lower() or "general"
        record = QueryRecord(
            id=uuid.uuid4().hex,
            raw_text=raw_text.strip(),
            user_id=safe_user_id,
            scope=safe_scope,
            domain=safe_domain,
            node_path=node_path,
            frozen_snapshot=frozen_snapshot,
            used_fallback=used_fallback,
            confidence=confidence,
            timestamp=time.time(),
            intent=str(intent or "unknown"),
            benefits_main_graph=bool(benefits_main_graph),
            new_nodes_created=max(0, int(new_nodes_created)),
            created_edges=max(0, int(created_edges)),
            credits_awarded=max(0, int(credits_awarded)),
            llm_used=bool(llm_used),
        )
        line = json.dumps(asdict(record), ensure_ascii=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fp:
                fp.write(line + "\n")
        return record

    def recent(self, limit: int = 20) -> List[QueryRecord]:
        if limit <= 0:
            return []
        with self._lock:
            records = self._read_records()
        items = records[-limit:]
        return list(reversed(items))

    def get_by_id(self, record_id: str) -> QueryRecord | None:
        needle = record_id.strip()
        if not needle:
            return None
        with self._lock:
            records = self._read_records()
        for record in reversed(records):
            if record.id == needle:
                return record
        return None

    def by_user(self, user_id: str, limit: int = 100) -> List[QueryRecord]:
        safe_user = user_id.strip() or "guest"
        safe_limit = max(1, min(5000, int(limit)))
        with self._lock:
            records = self._read_records()
        filtered = [record for record in records if record.user_id == safe_user]
        return list(reversed(filtered[-safe_limit:]))

    def _read_records(self) -> List[QueryRecord]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        records: List[QueryRecord] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            records.append(self._coerce_record(data))
        return records

    def _coerce_record(self, data: dict) -> QueryRecord:
        raw_text = str(data.get("raw_text", "")).strip()
        user_id = str(data.get("user_id", "")).strip()
        scope = str(data.get("scope", "")).strip().lower()
        domain = str(data.get("domain", "")).strip().lower()
        legacy = LEGACY_CONTEXT_RE.match(raw_text)
        if legacy:
            if not user_id:
                user_id = legacy.group("user").strip() or "guest"
            if scope not in VALID_SCOPES:
                scope = legacy.group("scope").strip().lower()
            raw_text = legacy.group("text").strip() or raw_text

        record_id = str(data.get("id", data.get("record_id", ""))).strip()
        if not record_id:
            record_id = self._derive_legacy_id(
                raw_text=raw_text,
                user_id=user_id,
                scope=scope,
                domain=domain,
                node_path=list(data.get("node_path", [])),
                frozen_snapshot=str(data.get("frozen_snapshot", "")),
                timestamp=float(data.get("timestamp", 0.0)),
            )
        if scope not in VALID_SCOPES:
            scope = "main"
        if not user_id:
            user_id = "guest"
        if not domain:
            domain = "general"

        return QueryRecord(
            id=record_id,
            raw_text=raw_text,
            user_id=user_id,
            scope=scope,
            domain=domain,
            node_path=list(data.get("node_path", [])),
            frozen_snapshot=str(data.get("frozen_snapshot", "")),
            used_fallback=bool(data.get("used_fallback", False)),
            confidence=float(data.get("confidence", 0.0)),
            timestamp=float(data.get("timestamp", 0.0)),
            intent=str(data.get("intent", "unknown")),
            benefits_main_graph=bool(data.get("benefits_main_graph", False)),
            new_nodes_created=max(0, int(data.get("new_nodes_created", 0))),
            created_edges=max(0, int(data.get("created_edges", 0))),
            credits_awarded=max(0, int(data.get("credits_awarded", 0))),
            llm_used=bool(data.get("llm_used", False)),
        )

    @staticmethod
    def _derive_legacy_id(
        *,
        raw_text: str,
        user_id: str,
        scope: str,
        domain: str,
        node_path: List[str],
        frozen_snapshot: str,
        timestamp: float,
    ) -> str:
        payload = {
            "raw_text": raw_text,
            "user_id": user_id,
            "scope": scope,
            "domain": domain,
            "node_path": node_path,
            "frozen_snapshot": frozen_snapshot,
            "timestamp": timestamp,
        }
        blob = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()
