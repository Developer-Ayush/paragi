"""encoder/embedding_encoder.py — Semantic vector encoder.

Ported from OwnEncoder and TemporaryEncoder in app/query_pipeline.py and app/own_encoder.py.
Produces a 700-dim semantic vector using hash embedding or fastembed.
"""
from __future__ import annotations

import hashlib
import math
from typing import Iterable, List

from core.constants import (
    SEMANTIC_DIMS, RANGE_VISCERAL_STATES, RANGE_EMOTIONAL_RANGE,
    DOMAIN_ANCHOR_DIMS,
)
from app.domain_policy import DOMAIN_KEYWORDS  # type: ignore  # reuse existing


class EmbeddingEncoder:
    """
    700-dimensional semantic encoder.

    Uses blake2s hash embedding by default. If fastembed is installed,
    uses BAAI/bge-small-en-v1.5 mapped into the bridge zone (250-579).
    Applies cognitive factor priors (§3.2) and domain anchors on top.
    """

    BIOLOGICAL_KW = {
        "sleep","hunger","thirst","tired","pain","breath","body","muscle","health",
        "energy","rest","vital","visceral","organ","heart","brain","nerve",
    }
    PSYCHOLOGICAL_KW = {
        "happy","sad","fear","anxiety","mood","think","feel","emotion","mind",
        "memory","will","drive","ego","self","desire","mental","focus",
    }
    SOCIAL_KW = {
        "friend","group","family","society","rule","law","community","other",
        "people","person","culture","norm","status","role","connect","social",
    }
    SITUATIONAL_KW = {
        "now","here","context","state","mode","event","task","goal","current",
        "environment","situation","incident","trigger","immediate","urgent",
    }
    INTELLECTUAL_KW = {
        "logic","reason","fact","learn","study","idea","concept","abstract",
        "knowledge","system","theory","method","complex","simple","skill",
    }

    def __init__(self, *, use_fastembed: bool = False) -> None:
        self._backend = "hash"
        self._embedder = None
        if use_fastembed:
            try:
                from fastembed import TextEmbedding  # type: ignore
                self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
                self._backend = "fastembed"
            except Exception:
                pass

    @property
    def backend(self) -> str:
        return self._backend

    def encode(self, tokens: List[str], text: str = "") -> List[float]:
        """Produce a 700-dim semantic vector for the given tokens and text."""
        vec = self._hash_embed_700(tokens or [text])
        self._apply_cognitive_factors(vec, tokens)
        self._apply_domain_priors(vec, tokens)

        if self._embedder is not None and text:
            bridge = self._fastembed_384(text)
            # Map 384-dim into dims 250-579 (bridge zone)
            for idx, val in enumerate(bridge):
                target = 250 + idx
                if target <= 579:
                    vec[target] = float(val)

        return self._normalize(vec)

    def _hash_embed_700(self, tokens: Iterable[str]) -> List[float]:
        dims = SEMANTIC_DIMS
        vec = [0.0] * dims
        general_ranges = [(70, 174), (250, 579), (670, 699)]
        available = sum(e - s + 1 for s, e in general_ranges)

        for token in tokens:
            digest = hashlib.blake2s(token.encode("utf-8"), digest_size=32).digest()
            for slot in range(10):
                b1 = digest[(slot * 2) % 32]
                b2 = digest[(slot * 2 + 1) % 32]
                raw_index = ((b1 << 8) | b2) % available
                curr, mapped = 0, 0
                for start, end in general_ranges:
                    size = end - start + 1
                    if curr + size > raw_index:
                        mapped = start + (raw_index - curr)
                        break
                    curr += size
                sign = 1.0 if digest[(slot + 13) % 32] % 2 == 0 else -1.0
                vec[mapped] += sign
        return vec

    def _fastembed_384(self, text: str) -> List[float]:
        try:
            values = next(iter(self._embedder.embed([text])))
            return self._normalize(list(values))
        except Exception:
            return [0.0] * 384

    def _apply_cognitive_factors(self, vec: List[float], tokens: List[str]) -> None:
        token_set = set(tokens)
        mappings = [
            (self.BIOLOGICAL_KW,    RANGE_VISCERAL_STATES),
            (self.PSYCHOLOGICAL_KW, RANGE_EMOTIONAL_RANGE),
            (self.SOCIAL_KW,        (280, 379)),
            (self.SITUATIONAL_KW,   (380, 479)),
            (self.INTELLECTUAL_KW,  (480, 579)),
        ]
        for keywords, (start, end) in mappings:
            hits = len(token_set & keywords)
            if hits > 0:
                mid = (start + end) // 2
                vec[mid] += min(1.2, 0.25 * hits)

    def _apply_domain_priors(self, vec: List[float], tokens: List[str]) -> None:
        token_set = set(tokens)
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = len(token_set & set(keywords))
            if score > 0:
                dim = DOMAIN_ANCHOR_DIMS.get(domain, DOMAIN_ANCHOR_DIMS["general"])
                vec[dim] += min(1.8, 0.35 * score)

    @staticmethod
    def _normalize(values: List[float]) -> List[float]:
        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 1e-12:
            return values
        return [v / norm for v in values]
