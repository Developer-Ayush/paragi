from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .domain_policy import DOMAIN_KEYWORDS
from .models import normalize_label


@dataclass(slots=True)
class OwnEncodedQuery:
    raw_text: str
    tokens: list[str]
    semantic_vector: list[float]  # 700 dims
    backend: str


class OwnEncoder:
    token_re = re.compile(r"[a-z0-9_]+")
    # §3.2 named dimension ranges
    RANGE_DECISION_FATIGUE = (0, 29)
    RANGE_VISCERAL_STATES = (30, 69)
    RANGE_EMOTIONAL_RANGE = (175, 209)
    RANGE_PSYCHOLOGICAL_BLOCK = (210, 249)
    RANGE_FACTUAL_WORLD = (580, 639)
    RANGE_CAUSAL_RELATIONAL = (640, 669)

    domain_anchor_dims: dict[str, int] = {
        "general": 582,
        "medical": 596,
        "legal": 607,
        "physics": 618,
        "finance": 629,
        "technology": 638,
    }

    def __init__(self, *, model_path: Path | None = None) -> None:
        self._backend = "own"
        self.model_path = model_path
        self._token_weights: Dict[str, List[Tuple[int, float]]] = {}
        if model_path is not None:
            self._load_model(model_path)

    def encode(self, text: str) -> OwnEncodedQuery:
        normalized = normalize_label(text)
        tokens = self.token_re.findall(normalized)
        vec = self._hash_embed_700(tokens or [normalized])
        self._apply_domain_priors(vec, tokens)
        self._apply_learned_weights(vec, tokens)
        return OwnEncodedQuery(
            raw_text=normalized,
            tokens=tokens,
            semantic_vector=self._normalize(vec),
            backend=self._backend,
        )

    def _hash_embed_700(self, tokens: Iterable[str]) -> list[float]:
        dims = 700
        vec = [0.0] * dims
        for token in tokens:
            digest = hashlib.blake2s(token.encode("utf-8"), digest_size=32).digest()
            # Map into general knowledge range (not reserved for specific semantics)
            # Reserved ranges from §3.2: 0-69, 175-249, 580-669
            # General ranges: 70-174, 250-579, 670-699
            general_ranges = [(70, 174), (250, 579), (670, 699)]
            available_dims = sum(r[1] - r[0] + 1 for r in general_ranges)

            for slot in range(10):
                b1 = digest[(slot * 2) % 32]
                b2 = digest[(slot * 2 + 1) % 32]
                raw_index = ((b1 << 8) | b2) % available_dims

                # Map raw_index back to general_ranges
                curr = 0
                mapped_index = 0
                for start, end in general_ranges:
                    size = end - start + 1
                    if curr + size > raw_index:
                        mapped_index = start + (raw_index - curr)
                        break
                    curr += size

                sign = 1.0 if digest[(slot + 13) % 32] % 2 == 0 else -1.0
                vec[mapped_index] += sign
        return vec

    def _apply_domain_priors(self, vec: list[float], tokens: list[str]) -> None:
        if not tokens:
            return
        token_set = set(tokens)
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = len(token_set.intersection(keywords))
            if score <= 0:
                continue
            dim = self.domain_anchor_dims.get(domain, self.domain_anchor_dims["general"])
            vec[dim] += min(1.8, 0.35 * score)

    def _apply_learned_weights(self, vec: list[float], tokens: list[str]) -> None:
        if not self._token_weights or not tokens:
            return
        for token in tokens:
            for dim, weight in self._token_weights.get(token, []):
                if 0 <= dim < len(vec):
                    vec[dim] += float(weight)

    @staticmethod
    def _normalize(values: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 1e-12:
            return values
        return [v / norm for v in values]

    def _load_model(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        weights = payload.get("token_weights", {})
        if not isinstance(weights, dict):
            return

        loaded: Dict[str, List[Tuple[int, float]]] = {}
        for token, pairs in weights.items():
            if not isinstance(token, str) or not isinstance(pairs, list):
                continue
            clean_pairs: list[Tuple[int, float]] = []
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2:
                    continue
                dim = int(pair[0])
                weight = float(pair[1])
                if 0 <= dim < 700 and abs(weight) > 1e-9:
                    clean_pairs.append((dim, weight))
            if clean_pairs:
                loaded[token] = clean_pairs
        self._token_weights = loaded

    def _save_model(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            "version": 1,
            "backend": self._backend,
            "updated_at": time.time(),
            "token_weights": {
                token: [[dim, weight] for dim, weight in pairs]
                for token, pairs in self._token_weights.items()
            },
        }
        path.write_text(json.dumps(serializable, ensure_ascii=True), encoding="utf-8")

    def train_from_records(
        self,
        records_path: Path,
        *,
        max_records: int = 50000,
        min_confidence: float = 0.3,
        min_token_occurrences: int = 2,
    ) -> dict:
        if max_records <= 0:
            return {"trained_tokens": 0, "records_used": 0}
        if not records_path.exists():
            return {"trained_tokens": 0, "records_used": 0}

        token_counts: Dict[str, int] = {}
        token_domain_scores: Dict[str, Dict[str, float]] = {}
        token_recall_scores: Dict[str, float] = {}
        records_used = 0

        lines = records_path.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            if records_used >= max_records:
                break
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue

            confidence = float(row.get("confidence", 0.0))
            if confidence < min_confidence:
                continue

            text = normalize_label(str(row.get("raw_text", "")))
            if not text:
                continue
            tokens = self.token_re.findall(text)
            if not tokens:
                continue

            domain = str(row.get("domain", "general")).strip().lower() or "general"
            signal = max(0.1, min(1.0, confidence))
            if row.get("used_fallback"):
                signal *= 1.05

            for token in tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
                token_recall_scores[token] = token_recall_scores.get(token, 0.0) + signal
                dmap = token_domain_scores.setdefault(token, {})
                dmap[domain] = dmap.get(domain, 0.0) + signal

            records_used += 1

        next_weights: Dict[str, List[Tuple[int, float]]] = {}
        for token, count in token_counts.items():
            if count < min_token_occurrences:
                continue
            domain_scores = token_domain_scores.get(token, {})
            if not domain_scores:
                continue

            best_domain = max(domain_scores, key=domain_scores.get)
            anchor_dim = self.domain_anchor_dims.get(best_domain, self.domain_anchor_dims["general"])
            mean_signal = token_recall_scores.get(token, 0.0) / max(1, count)
            domain_signal = domain_scores.get(best_domain, 0.0) / max(1, count)
            weight = min(1.5, (0.45 * mean_signal) + (0.55 * domain_signal))
            if weight <= 0.05:
                continue
            next_weights[token] = [(anchor_dim, round(weight, 6))]

        self._token_weights = next_weights
        if self.model_path is not None:
            self._save_model(self.model_path)

        return {
            "trained_tokens": len(next_weights),
            "records_used": records_used,
            "model_path": str(self.model_path) if self.model_path is not None else "",
            "backend": self._backend,
        }
