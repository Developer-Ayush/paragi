from __future__ import annotations

import json
import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

from decoder.graph_translator import GraphTranslator
from models.models import EdgeType

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

class GraphTranslatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"translator_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.translator = GraphTranslator(model_name="phi3", data_dir=self.case_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.case_dir, ignore_errors=True)

    @patch("ollama.generate")
    def test_encode_returns_correct_keys(self, mock_generate) -> None:
        mock_generate.return_value = {
            "response": json.dumps({
                "source": "fire",
                "relation": "CAUSES",
                "target": "burn",
                "confidence": 0.9
            })
        }
        res = self.translator.encode("fire causes burn")
        self.assertIn("source", res)
        self.assertIn("relation", res)
        self.assertIn("target", res)
        self.assertIn("confidence", res)
        self.assertIn("fallback_used", res)
        self.assertFalse(res["fallback_used"])

    @patch("ollama.generate")
    def test_encode_relation_is_valid(self, mock_generate) -> None:
        valid_rels = [e.value for e in EdgeType]
        mock_generate.return_value = {
            "response": json.dumps({
                "source": "fire",
                "relation": "INVALID_REL",
                "target": "burn",
                "confidence": 0.9
            })
        }
        res = self.translator.encode("fire causes burn")
        self.assertIn(res["relation"], valid_rels)
        self.assertEqual(res["relation"], "INFERRED")

    @patch("ollama.generate")
    def test_decode_returns_non_empty_string(self, mock_generate) -> None:
        mock_generate.return_value = {"response": "Fire can cause a burn."}
        path = [{"source": "fire", "relation": "CAUSES", "target": "burn", "strength": 0.9}]
        answer, fallback = self.translator.decode(path, 0.9)
        self.assertTrue(len(answer) > 0)
        self.assertFalse(fallback)

    def test_encode_fallback_works(self) -> None:
        # Ensure ollama fails by not patching it or forcing an exception if needed,
        # but here we just test the internal fallback method directly or by letting ollama fail.
        with patch("ollama.generate", side_effect=Exception("Ollama down")):
            res = self.translator.encode("The cat sat on the mat")
            self.assertTrue(res["fallback_used"])
            self.assertEqual(res["relation"], "INFERRED")

    def test_decode_fallback_works(self) -> None:
        with patch("ollama.generate", side_effect=Exception("Ollama down")):
            path = [{"source": "fire", "relation": "CAUSES", "target": "burn", "strength": 0.9}]
            answer, fallback = self.translator.decode(path, 0.9)
            self.assertTrue(fallback)
            self.assertIn("fire causes burn", answer.lower())

    @patch("ollama.generate")
    def test_logs_are_written(self, mock_generate) -> None:
        mock_generate.return_value = {"response": json.dumps({"source":"a", "relation":"IS_A", "target":"b", "confidence":1.0})}
        self.translator.encode("a is a b")
        self.assertTrue(self.translator.encoder_log_path.exists())

        mock_generate.return_value = {"response": "A is a B."}
        self.translator.decode([{"source":"a", "relation":"IS_A", "target":"b"}], 1.0)
        self.assertTrue(self.translator.decoder_log_path.exists())

if __name__ == "__main__":
    unittest.main()
