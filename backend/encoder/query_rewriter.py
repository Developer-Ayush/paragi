from __future__ import annotations

import difflib
import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set

from core.domain_policy import DOMAIN_KEYWORDS
from models.models import normalize_label


@dataclass(slots=True)
class RewriteCorrection:
    source: str
    target: str
    score: float


@dataclass(slots=True)
class RewriteResult:
    original_text: str
    rewritten_text: str
    changed: bool
    confidence: float
    corrections: List[RewriteCorrection]


class QueryRewriter:
    _token_re = __import__("re").compile(r"[a-z0-9_]+")
    _base_tokens: Set[str] = {
        "what",
        "is",
        "my",
        "name",
        "who",
        "am",
        "i",
        "where",
        "do",
        "live",
        "work",
        "email",
        "phone",
        "address",
        "does",
        "can",
        "could",
        "will",
        "fire",
        "burn",
        "steam",
        "heat",
        "water",
        "cold",
        "why",
        "how",
        "when",
        "explain",
        "define",
        "tell",
        "about",
        "relationship",
        "between",
        "because",
        "causes",
        "cause",
        "correlates",
    }
    _common_tokens: Set[str] = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "were",
        "with",
        "today",
        "todays",
    }

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._learned_map: Dict[str, Dict[str, float]] = {}
        self._load()

    def rewrite(self, text: str, *, extra_terms: Iterable[str] | None = None) -> RewriteResult:
        original = text.strip()
        normalized = normalize_label(original)
        tokens = self._token_re.findall(normalized)
        if not tokens:
            return RewriteResult(
                original_text=original,
                rewritten_text=normalized,
                changed=False,
                confidence=1.0,
                corrections=[],
            )

        vocab = self._build_vocab(extra_terms or [])
        locked_indexes = self._locked_token_indexes(tokens)
        # print(f"DEBUG_REWRITE: tokens={tokens} locked={locked_indexes} vocab_size={len(vocab)}")
        corrections: list[RewriteCorrection] = []
        out_tokens: list[str] = []
        for idx, token in enumerate(tokens):
            if idx in locked_indexes:
                out_tokens.append(token)
                continue
            if token in vocab or token in self._common_tokens or len(token) <= 3:
                out_tokens.append(token)
                continue

            correction = self._correct_token(token, vocab)
            if correction is None:
                out_tokens.append(token)
                continue

            out_tokens.append(correction.target)
            corrections.append(correction)

        rewritten = " ".join(out_tokens).strip()
        changed = rewritten != normalized
        confidence = 1.0
        if corrections:
            confidence = sum(item.score for item in corrections) / len(corrections)

        return RewriteResult(
            original_text=original,
            rewritten_text=rewritten or normalized,
            changed=changed,
            confidence=float(confidence),
            corrections=corrections,
        )

    def reinforce(self, result: RewriteResult, *, reward: float) -> None:
        if not result.corrections:
            return
        bounded_reward = max(0.0, min(1.0, float(reward)))
        if bounded_reward <= 0.0:
            return

        with self._lock:
            dirty = False
            for correction in result.corrections:
                source = correction.source
                target = correction.target
                base = correction.score * bounded_reward
                row = self._learned_map.setdefault(source, {})
                row[target] = row.get(target, 0.0) + base
                dirty = True
            if dirty:
                self._save()

    def _build_vocab(self, extra_terms: Iterable[str]) -> Set[str]:
        vocab = set(self._base_tokens)
        for terms in DOMAIN_KEYWORDS.values():
            vocab.update(terms)
        with self._lock:
            for row in self._learned_map.values():
                vocab.update(row.keys())
        for term in extra_terms:
            for token in self._token_re.findall(normalize_label(term)):
                vocab.add(token)
        return vocab

    # Patterns that indicate the subject starts at a specific token index.
    # Format: list of (prefix_tokens_tuple, subject_start_offset)
    _concept_prefixes = [
        (("who", "is"), 2),
        (("who", "was"), 2),
        (("who", "are"), 2),
        (("define",), 1),
        (("describe",), 1),
        (("explain",), 1),
        (("tell", "me", "about"), 3),
        (("how", "much"), 2),
        (("how", "many"), 2),
        (("how", "big"), 2),
        (("how", "old"), 2),
        (("how", "tall"), 2),
        (("how", "fast"), 2),
        (("how", "far"), 2),
        (("how", "long"), 2),
        (("how", "do"), 2),
        (("how", "does"), 2),
        (("how", "did"), 2),
        (("how", "is"), 2),
        (("how", "are"), 2),
        (("where", "is"), 2),
        (("where", "are"), 2),
        (("where", "do"), 2),
        (("where", "does"), 2),
        (("when", "is"), 2),
        (("when", "was"), 2),
        (("when", "did"), 2),
        (("why", "is"), 2),
        (("why", "are"), 2),
        (("why", "do"), 2),
        (("why", "does"), 2),
    ]

    def _locked_token_indexes(self, tokens: list[str]) -> set[int]:
        locked: set[int] = set()
        if len(tokens) >= 4 and tokens[0] == "my" and "is" in tokens[1:]:
            # Preserve personal declarations exactly to avoid distorting private facts.
            is_index = tokens.index("is", 1)
            locked.update(range(1, len(tokens)))
            if is_index + 1 < len(tokens):
                locked.update(range(is_index + 1, len(tokens)))
            return locked
        if len(tokens) >= 3 and tokens[0] == "my" and tokens[1] == "name" and tokens[2] == "is":
            locked.update(range(3, len(tokens)))
            return locked
        if len(tokens) >= 2 and tokens[0] == "i" and tokens[1] == "am":
            locked.update(range(2, len(tokens)))
            return locked
        if len(tokens) >= 3 and tokens[0] == "i" and tokens[1] == "live" and tokens[2] == "in":
            locked.update(range(3, len(tokens)))
            return locked
        if len(tokens) >= 2 and tokens[0] == "i" and tokens[1] == "like":
            locked.update(range(2, len(tokens)))
            return locked

        # Lock subject tokens in concept/question queries so proper nouns
        # and domain terms are never rewritten.
        for prefix, offset in self._concept_prefixes:
            if len(tokens) >= offset + 1 and tuple(tokens[:len(prefix)]) == prefix:
                locked.update(range(offset, len(tokens)))
                return locked

        # For general "<subject> is <object>" fact patterns, lock everything.

        return locked

    def _correct_token(self, token: str, vocab: Set[str]) -> RewriteCorrection | None:
        learned = self._best_learned(token)
        if learned is not None:
            return learned

        candidates = list(vocab)
        close = difflib.get_close_matches(token, candidates, n=1, cutoff=0.72)
        if not close:
            return None

        target = close[0]
        score = difflib.SequenceMatcher(a=token, b=target).ratio()
        if score < 0.70:
            return None
        return RewriteCorrection(source=token, target=target, score=score)

    def _best_learned(self, token: str) -> RewriteCorrection | None:
        with self._lock:
            row = self._learned_map.get(token)
            if not row:
                return None
            target = max(row, key=row.get)
            strength = row[target]
        # Learned mappings are trusted but still bounded.
        score = max(0.7, min(0.99, strength))
        return RewriteCorrection(source=token, target=target, score=score)

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        mappings = payload.get("mappings", {})
        if not isinstance(mappings, dict):
            return
        loaded: Dict[str, Dict[str, float]] = {}
        for src, row in mappings.items():
            if not isinstance(src, str) or not isinstance(row, dict):
                continue
            clean_row: Dict[str, float] = {}
            for dst, score in row.items():
                if not isinstance(dst, str):
                    continue
                try:
                    clean_row[dst] = float(score)
                except Exception:
                    continue
            if clean_row:
                loaded[src] = clean_row
        self._learned_map = loaded

    def _save(self) -> None:
        payload = {
            "version": 1,
            "mappings": self._learned_map,
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
