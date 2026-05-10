"""encoder/embedding_encoder.py — Core semantic vector embedding logic."""
from __future__ import annotations

import hashlib
import math
from typing import Iterable, List, Optional
from core.constants import SEMANTIC_DIMS


class EmbeddingEncoder:
    """
    Core semantic vector encoder.
    Produces high-dimensional vectors (700-dim) using structural hashing 
    and cognitive priors.
    """

    def __init__(self, use_fastembed: bool = False):
        self._embedder = None
        if use_fastembed:
            try:
                from fastembed import TextEmbedding
                self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            except ImportError:
                pass

    def encode_tokens(self, tokens: Iterable[str]) -> List[float]:
        """Produce a sparse semantic vector from tokens."""
        dims = SEMANTIC_DIMS
        vec = [0.0] * dims
        # Use blake2s for stable structural hashing
        for token in tokens:
            digest = hashlib.blake2s(token.encode("utf-8"), digest_size=32).digest()
            for i in range(5):
                idx = ((digest[i*2] << 8) | digest[i*2+1]) % dims
                vec[idx] += 1.0
        return self._normalize(vec)

    def encode_text(self, text: str) -> List[float]:
        """Produce a dense semantic vector from text using fastembed if available."""
        if self._embedder:
            embeddings = list(self._embedder.embed([text]))
            return self._normalize(list(embeddings[0]))
        return self.encode_tokens(text.split())

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        norm = math.sqrt(sum(v*v for v in vec))
        return [v/norm for v in vec] if norm > 0 else vec
