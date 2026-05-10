from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from graph.graph import PathMatch
from models.models import EdgeType
from decoder.own_decoder import OwnDecoder

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class OwnDecoderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"owndec_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.case_dir / "decoder_model.json"
        self.records_path = self.case_dir / "decoder_training.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_decode_path_is_natural_text(self) -> None:
        dec = OwnDecoder(model_path=self.model_path)
        path = PathMatch(
            node_ids=["n1", "n2"],
            node_labels=["fire", "burn"],
            edge_ids=["e1"],
            edge_types=[EdgeType.CAUSES],
            edge_strengths=[0.9],
            hops=1,
            mean_strength=0.9,
            goal_relevance=1.0,
            score=0.9,
        )
        out = dec.decode_path(path)
        self.assertIn("fire", out.lower())
        self.assertIn("burn", out.lower())
        self.assertNotIn("connected to", out.lower())

    def test_train_from_records_creates_model(self) -> None:
        rows = [
            {
                "raw_text": "does steam burn",
                "answer": "Steam can cause burn.",
                "confidence": 0.86,
            },
            {
                "raw_text": "does fire burn",
                "answer": "Fire can cause burn.",
                "confidence": 0.92,
            },
        ]
        self.records_path.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8")

        dec = OwnDecoder(model_path=self.model_path)
        summary = dec.train_from_records(
            self.records_path,
            max_records=100,
            min_confidence=0.1,
            min_samples=1,
        )
        self.assertTrue(summary["updated"])
        self.assertGreaterEqual(summary["records_used"], 1)
        self.assertTrue(self.model_path.exists())


if __name__ == "__main__":
    unittest.main()
