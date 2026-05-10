from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil

from utils.bloom import BloomFilter

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class BloomFilterTests(unittest.TestCase):
    def test_add_and_contains(self) -> None:
        bloom = BloomFilter(capacity=1000, error_rate=0.001)
        bloom.add("fire")
        bloom.add("burn")
        self.assertIn("fire", bloom)
        self.assertIn("burn", bloom)
        self.assertNotIn("unknown-concept", bloom)

    def test_persistence_round_trip(self) -> None:
        bloom = BloomFilter(capacity=1000, error_rate=0.001)
        bloom.add("steam")
        bloom.add("temperature")

        case_dir = TEST_TMP_ROOT / f"bloom_{uuid.uuid4().hex}"
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            path = case_dir / "nodes.bloom.json"
            bloom.save(path)
            loaded = BloomFilter.load(path)
            self.assertIn("steam", loaded)
            self.assertIn("temperature", loaded)
            self.assertNotIn("random", loaded)
        finally:
            shutil.rmtree(case_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
