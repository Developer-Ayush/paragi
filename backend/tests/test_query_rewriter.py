from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from encoder.query_rewriter import QueryRewriter

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class QueryRewriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"rewriter_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.case_dir / "query_rewriter.json"
        self.rewriter = QueryRewriter(self.path)

    def tearDown(self) -> None:
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_rewrites_common_typo(self) -> None:
        result = self.rewriter.rewrite("what is my naem")
        self.assertTrue(result.changed)
        self.assertEqual(result.rewritten_text, "what is my name")
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_reinforce_persists_mapping(self) -> None:
        first = self.rewriter.rewrite("what is my naem")
        self.rewriter.reinforce(first, reward=0.9)

        second = QueryRewriter(self.path).rewrite("what is my naem")
        self.assertEqual(second.rewritten_text, "what is my name")
        self.assertTrue(second.changed)

    def test_preserves_generic_personal_fact_sentence(self) -> None:
        result = self.rewriter.rewrite("my bib number for todays race is 10")
        self.assertFalse(result.changed)
        self.assertEqual(result.rewritten_text, "my bib number for todays race is 10")


if __name__ == "__main__":
    unittest.main()
