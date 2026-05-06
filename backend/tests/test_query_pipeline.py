from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from app.bloom import BloomFilter
from app.graph import GraphEngine
from app.models import EdgeType
from app.query_pipeline import QueryPipeline, TemporaryDecoder, TemporaryEncoder
from app.storage import InMemoryGraphStore

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class QueryPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"pipeline_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        bloom_path = self.case_dir / "nodes.bloom.json"
        self.graph = GraphEngine(
            store=InMemoryGraphStore(),
            bloom=BloomFilter(capacity=5000, error_rate=0.001),
            bloom_path=bloom_path,
            edge_strength_floor=0.001,
            edge_decay_per_cycle=0.01,
        )
        self.pipeline = QueryPipeline(self.graph, TemporaryEncoder(use_fastembed=False), TemporaryDecoder())

    def tearDown(self) -> None:
        self.graph.close()
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_relation_query_uses_internal_path(self) -> None:
        self.graph.create_edge("steam", "heat", EdgeType.IS_A, strength=0.9)
        self.graph.create_edge("heat", "burn", EdgeType.CAUSES, strength=0.9)

        result = self.pipeline.run("does steam burn?")
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.source, "steam")
        self.assertEqual(result.target, "burn")
        self.assertIn("steam", result.answer.lower())
        self.assertGreaterEqual(len(result.node_path), 2)

    def test_relation_query_fallback_then_learns(self) -> None:
        first = self.pipeline.run("does steam burn?")
        self.assertTrue(first.used_fallback)
        self.assertGreaterEqual(first.created_edges, 1)

        second = self.pipeline.run("does steam burn?")
        self.assertFalse(second.used_fallback)
        self.assertEqual(second.target, "burn")

    def test_concept_query_summarizes_neighbors(self) -> None:
        self.graph.create_edge("fire", "smoke", EdgeType.CORRELATES, strength=0.8)
        result = self.pipeline.run("what is fire?")
        self.assertIn("smoke", result.answer.lower())
        self.assertFalse(result.used_fallback)

    def test_concept_query_supports_describe_style_prompts(self) -> None:
        self.graph.create_edge("photosynthesis", "plants", EdgeType.CORRELATES, strength=0.83)
        result = self.pipeline.run("describe photosynthesis")
        self.assertIn("plants", result.answer.lower())
        self.assertFalse(result.used_fallback)
        self.assertTrue(any(step == "intent:concept" for step in result.steps))

    def test_unknown_query_returns_guidance(self) -> None:
        result = self.pipeline.run("tell me something interesting")
        self.assertIn("relation questions", result.answer.lower())
        self.assertFalse(result.used_fallback)

    def test_personal_fact_is_stored(self) -> None:
        result = self.pipeline.run("my name is ayush")
        self.assertIn("remember your name", result.answer.lower())
        self.assertEqual(result.source, "self")
        self.assertEqual(result.target, "name ayush")
        self.assertGreaterEqual(result.created_edges, 1)
        self.assertTrue(self.graph.node_exists("name ayush"))

    def test_personal_query_reads_memory(self) -> None:
        _ = self.pipeline.run("i am ayush anand")
        result = self.pipeline.run("what is my name")
        self.assertEqual(result.source, "self")
        self.assertIn("your name is ayush anand", result.answer.lower())
        self.assertFalse(result.used_fallback)

    def test_nationality_personal_memory(self) -> None:
        stored = self.pipeline.run("my nationality is indian")
        self.assertEqual(stored.source, "self")
        self.assertEqual(stored.target, "nationality indian")
        result = self.pipeline.run("what is my nationality")
        self.assertIn("your nationality is indian", result.answer.lower())

    def test_generic_personal_fact_and_query(self) -> None:
        stored = self.pipeline.run("my bib number for todays race is 10")
        self.assertEqual(stored.source, "self")
        self.assertEqual(stored.target, "bib number for todays race 10")
        result = self.pipeline.run("what is my bib number for todays race")
        self.assertIn("your bib number for todays race is 10", result.answer.lower())


if __name__ == "__main__":
    unittest.main()
