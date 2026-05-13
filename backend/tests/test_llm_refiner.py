import unittest
from unittest.mock import patch, MagicMock
from backend.utils.llm_refiner import LLMRefiner
import json
import io

class TestLLMRefinerOpenRouter(unittest.TestCase):
    def setUp(self):
        self.refiner = LLMRefiner(
            backend="groq",
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            base_url="https://openrouter.ai",
            api_key="test_key"
        )

    @patch("urllib.request.urlopen")
    def test_refine_answer_success(self, mock_urlopen):
        # Mock response from OpenRouter
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": "This is a refined answer."
                }
            }]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = self.refiner.refine_answer(
            question="What is fire?",
            base_answer="Fire is hot.",
            node_path=["fire", "hot"],
            confidence=0.9,
            scope="main",
            domain="general",
            used_fallback=False
        )

        self.assertTrue(result.used)
        self.assertEqual(result.answer, "This is a refined answer.")
        self.assertEqual(result.backend, "groq")
        self.assertIsNone(result.error)

    def test_status_groq(self):
        status = self.refiner.status()
        self.assertEqual(status["backend"], "groq")
        self.assertTrue(status["enabled"])
        self.assertTrue(status["reachable"])
        self.assertEqual(status["available_models"], ["google/gemini-2.0-flash-lite-preview-02-05:free"])

    def test_disabled_backend(self):
        disabled_refiner = LLMRefiner(backend="none", model="", base_url="")
        result = disabled_refiner.refine_answer(
            question="What is fire?",
            base_answer="Fire is hot.",
            node_path=[],
            confidence=0.5,
            scope="main",
            domain="general",
            used_fallback=False
        )
        self.assertFalse(result.used)
        self.assertEqual(result.answer, "Fire is hot.")

if __name__ == "__main__":
    unittest.main()
