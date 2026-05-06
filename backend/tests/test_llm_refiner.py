from __future__ import annotations

import unittest

from app.llm_refiner import LLMRefiner


class LLMRefinerTests(unittest.TestCase):
    def test_none_backend_passthrough(self) -> None:
        refiner = LLMRefiner(
            backend="none",
            model="gemma3:4b",
            base_url="http://127.0.0.1:11434",
        )
        out = refiner.refine_answer(
            question="does fire burn?",
            base_answer="Fire can cause burn.",
            node_path=["fire", "burn"],
            confidence=0.8,
            scope="main",
            domain="general",
            used_fallback=False,
        )
        self.assertEqual(out.answer, "Fire can cause burn.")
        self.assertFalse(out.used)
        self.assertIsNone(out.error)

        status = refiner.status()
        self.assertEqual(status["backend"], "none")
        self.assertFalse(status["enabled"])

    def test_ollama_backend_falls_back_when_unreachable(self) -> None:
        refiner = LLMRefiner(
            backend="ollama",
            model="gemma3:4b",
            base_url="http://127.0.0.1:1",
            timeout_seconds=1.0,
        )
        out = refiner.refine_answer(
            question="does fire burn?",
            base_answer="Fire can cause burn.",
            node_path=["fire", "burn"],
            confidence=0.8,
            scope="main",
            domain="general",
            used_fallback=False,
        )
        self.assertEqual(out.answer, "Fire can cause burn.")
        self.assertFalse(out.used)
        self.assertIsNotNone(out.error)

        status = refiner.status()
        self.assertEqual(status["backend"], "ollama")
        self.assertFalse(status["reachable"])


if __name__ == "__main__":
    unittest.main()
