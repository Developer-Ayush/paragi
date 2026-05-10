from __future__ import annotations

import shutil
import unittest
import uuid
from pathlib import Path

from utils.bloom import BloomFilter
from graph.expansion import ExpansionQueueStore, ExpansionResolver
from utils.external_sources import ExternalKnowledgeConnector, RelationCandidate
from graph.graph import GraphEngine
from models.models import EdgeType
from cognition.consciousness import QueryPipeline, TemporaryDecoder, TemporaryEncoder
from graph.persistence.storage import InMemoryGraphStore

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class MockConnector(ExternalKnowledgeConnector):
    name = "mock"

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 4.0):
        if source == "copper" and target == "conduct":
            return [RelationCandidate(source="copper", target="conduct", edge_type=EdgeType.CORRELATES, strength=0.8, source_name=self.name)]
        return []


class Phase4ExpansionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"phase4_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)

        bloom_path = self.case_dir / "nodes.bloom.json"
        queue_path = self.case_dir / "expansion_queue.json"

        self.graph = GraphEngine(
            store=InMemoryGraphStore(),
            bloom=BloomFilter(capacity=5000, error_rate=0.001),
            bloom_path=bloom_path,
            edge_strength_floor=0.001,
            edge_decay_per_cycle=0.01,
        )
        self.queue = ExpansionQueueStore(queue_path)
        self.resolver = ExpansionResolver(self.graph, self.queue, connectors=[MockConnector()])
        self.pipeline = QueryPipeline(
            self.graph,
            TemporaryEncoder(use_fastembed=False),
            TemporaryDecoder(),
            expansion_queue=self.queue,
            expansion_resolver=self.resolver,
        )

    def tearDown(self) -> None:
        self.graph.close()
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_activation_shortcut_collapses_dims(self) -> None:
        self.graph.create_edge("steam", "heat", EdgeType.IS_A, strength=0.9)
        self.graph.create_edge("heat", "burn", EdgeType.CAUSES, strength=0.9)

        first = self.pipeline.run("does steam burn?")
        second = self.pipeline.run("does steam burn?")
        third = self.pipeline.run("does steam burn?")
        fourth = self.pipeline.run("does steam burn?")

        self.assertGreater(first.active_dims, fourth.active_dims)
        self.assertFalse(second.shortcut_applied)
        self.assertTrue(fourth.shortcut_applied)
        self.assertGreaterEqual(len(first.activation_ranges), 1)

    def test_expansion_queue_and_resolution_flow(self) -> None:
        result = self.pipeline.run("does copper conduct?")
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.target, "conduct")
        self.assertIsNotNone(result.expansion_node_id)
        self.assertIn("copper", result.answer.lower())

        nodes = self.queue.list_recent(limit=5)
        self.assertGreaterEqual(len(nodes), 1)
        self.assertEqual(nodes[0].status, "resolved")


if __name__ == "__main__":
    unittest.main()

