"""
graph/persistence/bloom.py — Bloom Filter for fast existence checks (§2.1).
"""
from __future__ import annotations

import hashlib
import zlib
from typing import Set


class BloomFilter:
    """
    A simple Bloom Filter to avoid unnecessary graph lookups.
    """

    def __init__(self, size: int = 10000, hash_count: int = 7) -> None:
        self.size = size
        self.hash_count = hash_count
        self.bit_array = [0] * size
        self._added_count = 0

    def add(self, string: str) -> None:
        """Add a string to the filter."""
        for seed in range(self.hash_count):
            result = self._hash(string, seed) % self.size
            self.bit_array[result] = 1
        self._added_count += 1

    def maybe_exists(self, string: str) -> bool:
        """
        Check if string might exist in the graph.
        Returns False if definitely NOT in graph.
        """
        for seed in range(self.hash_count):
            result = self._hash(string, seed) % self.size
            if self.bit_array[result] == 0:
                return False
        return True

    def _hash(self, string: str, seed: int) -> int:
        """Generate a hash for a string with a seed."""
        raw = f"{seed}:{string}".encode("utf-8")
        return zlib.adler32(raw) & 0xffffffff
