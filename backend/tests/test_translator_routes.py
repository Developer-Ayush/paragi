from __future__ import annotations

import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

class TranslatorRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"routes_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)

        self._old_key = os.environ.get("PARAGI_INTERNAL_KEY")
        self._old_data_dir = os.environ.get("PARAGI_DATA_DIR")
        os.environ["PARAGI_INTERNAL_KEY"] = "test_key"
        os.environ["PARAGI_DATA_DIR"] = str(self.case_dir)

    def tearDown(self) -> None:
        if self._old_key:
            os.environ["PARAGI_INTERNAL_KEY"] = self._old_key
        else:
            os.environ.pop("PARAGI_INTERNAL_KEY", None)

        if self._old_data_dir:
            os.environ["PARAGI_DATA_DIR"] = self._old_data_dir
        else:
            os.environ.pop("PARAGI_DATA_DIR", None)

        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_encode_decode_401_without_key(self) -> None:
        with TestClient(app) as client:
            res_enc = client.post("/internal/encode", json={"text": "hi"})
            self.assertEqual(res_enc.status_code, 401)

            res_dec = client.post("/internal/decode", json={"path": [{"s":"a","r":"b","t":"c"}], "confidence": 1.0})
            self.assertEqual(res_dec.status_code, 401)

    def test_encode_422_on_empty_text(self) -> None:
        with TestClient(app) as client:
            res = client.post("/internal/encode", json={"text": ""}, headers={"X-Internal-Key": "test_key"})
            self.assertEqual(res.status_code, 422)

    def test_decode_422_on_empty_path(self) -> None:
        with TestClient(app) as client:
            res = client.post("/internal/decode", json={"path": [], "confidence": 1.0}, headers={"X-Internal-Key": "test_key"})
            self.assertEqual(res.status_code, 422)

    @patch("app.graph_translator.GraphTranslator.encode")
    def test_valid_encode_request(self, mock_encode) -> None:
        mock_encode.return_value = {"source":"s", "relation":"IS_A", "target":"t", "confidence":0.8, "fallback_used":False}
        with TestClient(app) as client:
            res = client.post("/internal/encode", json={"text": "s is a t"}, headers={"X-Internal-Key": "test_key"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["source"], "s")
            self.assertIn("fallback_used", data)

    @patch("app.graph_translator.GraphTranslator.decode")
    def test_valid_decode_request(self, mock_decode) -> None:
        mock_decode.return_value = ("S is a T.", False)
        with TestClient(app) as client:
            res = client.post("/internal/decode", json={"path": [{"source":"s","relation":"IS_A","target":"t"}], "confidence": 1.0}, headers={"X-Internal-Key": "test_key"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["answer"], "S is a T.")
            self.assertIn("fallback_used", data)

    def test_530_when_internal_key_not_set(self) -> None:
        with patch.dict(os.environ, {"PARAGI_INTERNAL_KEY": ""}, clear=True):
             with TestClient(app) as client:
                # Need to refresh the app state or mock os.getenv in the route
                # Actually, verify_internal_key reads it directly
                res = client.post("/internal/encode", json={"text": "hi"}, headers={"X-Internal-Key": "some_key"})
                self.assertEqual(res.status_code, 503)

if __name__ == "__main__":
    unittest.main()
