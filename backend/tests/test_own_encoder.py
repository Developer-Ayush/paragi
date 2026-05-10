from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from encoder.semantic_encoder import OwnEncoder

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class OwnEncoderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"ownenc_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.case_dir / "encoder_model.json"
        self.records_path = self.case_dir / "encoder_training.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_encode_outputs_700_dims(self) -> None:
        enc = OwnEncoder(model_path=self.model_path)
        out = enc.encode("what is javascript")
        self.assertEqual(out.backend, "own")
        self.assertEqual(len(out.semantic_vector), 700)
        self.assertGreater(len(out.tokens), 0)

    def test_train_from_records_creates_model(self) -> None:
        rows = [
            {
                "raw_text": "what is javascript",
                "domain": "technology",
                "confidence": 0.8,
                "used_fallback": True,
            },
            {
                "raw_text": "javascript server api",
                "domain": "technology",
                "confidence": 0.9,
                "used_fallback": False,
            },
        ]
        self.records_path.write_text("\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8")
        enc = OwnEncoder(model_path=self.model_path)
        summary = enc.train_from_records(
            self.records_path,
            max_records=100,
            min_confidence=0.1,
            min_token_occurrences=1,
        )
        self.assertGreaterEqual(summary["trained_tokens"], 1)
        self.assertTrue(self.model_path.exists())


if __name__ == "__main__":
    unittest.main()
