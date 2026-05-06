from __future__ import annotations

import base64
import hashlib
import json
import math
import threading
from pathlib import Path


class BloomFilter:
    """Simple Bloom filter with JSON persistence."""

    def __init__(self, capacity: int, error_rate: float, *, num_bits: int | None = None, num_hashes: int | None = None) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if not (0 < error_rate < 1):
            raise ValueError("error_rate must be between 0 and 1")

        self.capacity = capacity
        self.error_rate = error_rate
        self.num_bits = num_bits or self._optimal_num_bits(capacity, error_rate)
        self.num_hashes = num_hashes or self._optimal_num_hashes(self.num_bits, capacity)
        self._bytes_len = (self.num_bits + 7) // 8
        self._bits = bytearray(self._bytes_len)
        self._lock = threading.RLock()

    @staticmethod
    def _optimal_num_bits(capacity: int, error_rate: float) -> int:
        value = -capacity * math.log(error_rate) / (math.log(2) ** 2)
        return max(8, int(value))

    @staticmethod
    def _optimal_num_hashes(num_bits: int, capacity: int) -> int:
        value = (num_bits / capacity) * math.log(2)
        return max(1, int(round(value)))

    def _hash_indexes(self, item: str) -> list[int]:
        data = item.encode("utf-8")
        indexes: list[int] = []
        for i in range(self.num_hashes):
            digest = hashlib.sha256(i.to_bytes(2, "big") + data).digest()
            indexes.append(int.from_bytes(digest[:8], "big") % self.num_bits)
        return indexes

    def add(self, item: str) -> None:
        with self._lock:
            for idx in self._hash_indexes(item):
                self._bits[idx // 8] |= 1 << (idx % 8)

    def __contains__(self, item: str) -> bool:
        with self._lock:
            for idx in self._hash_indexes(item):
                if not (self._bits[idx // 8] & (1 << (idx % 8))):
                    return False
            return True

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "capacity": self.capacity,
            "error_rate": self.error_rate,
            "num_bits": self.num_bits,
            "num_hashes": self.num_hashes,
            "bits_b64": base64.b64encode(bytes(self._bits)).decode("ascii"),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "BloomFilter":
        data = json.loads(path.read_text(encoding="utf-8"))
        bloom = cls(
            capacity=int(data["capacity"]),
            error_rate=float(data["error_rate"]),
            num_bits=int(data["num_bits"]),
            num_hashes=int(data["num_hashes"]),
        )
        bit_bytes = base64.b64decode(data["bits_b64"].encode("ascii"))
        if len(bit_bytes) != bloom._bytes_len:
            raise ValueError("Bloom filter bit-array length mismatch")
        bloom._bits[:] = bit_bytes
        return bloom

