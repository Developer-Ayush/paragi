from __future__ import annotations

import math
import unittest
import uuid
from pathlib import Path
import shutil

from utils.bloom import BloomFilter
from graph.graph import GraphEngine
from core.enums import EdgeType
from graph.persistence.storage import InMemoryGraphStore

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class GraphEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"graph_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        bloom_path = self.case_dir / "nodes.bloom.json"
        self.graph = GraphEngine(
            store=InMemoryGraphStore(),
            bloom=BloomFilter(capacity=5000, error_rate=0.001),
            bloom_path=bloom_path,
            edge_strength_floor=0.001,
            edge_decay_per_cycle=0.01,
        )

    def tearDown(self) -> None:
        self.graph.close()
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_create_nodes_and_edge_readback(self) -> None:
        edge = self.graph.create_edge("fire", "burn", EdgeType.CAUSES, strength=0.9)
        self.assertEqual(edge.type, EdgeType.CAUSES)
        self.assertGreater(edge.strength, 0.0)

        fetched = self.graph.get_edge("fire", "burn")
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched.type, EdgeType.CAUSES)

    def test_decay_never_below_floor(self) -> None:
        edge = self.graph.create_edge("fire", "heat", EdgeType.CORRELATES, strength=0.05)
        for _ in range(300):
            self.graph.decay_all_edges()
        decayed = self.graph.get_edge_by_id(edge.id)
        self.assertIsNotNone(decayed)
        assert decayed is not None
        self.assertGreaterEqual(decayed.strength, 0.001)

    def test_bootstrap_creates_typed_edges(self) -> None:
        created = self.graph.bootstrap_default()
        self.assertGreaterEqual(created, 6)
        edge = self.graph.get_edge("heat", "burn")
        self.assertIsNotNone(edge)
        assert edge is not None
        self.assertEqual(edge.type, EdgeType.CAUSES)

    def test_node_exists_uses_bloom_plus_store(self) -> None:
        self.assertFalse(self.graph.node_exists("gravity"))
        self.graph.create_or_get_node("gravity")
        self.assertTrue(self.graph.node_exists("gravity"))

    def test_find_paths_multi_hop(self) -> None:
        self.graph.create_edge("steam", "water", EdgeType.CORRELATES, strength=0.87)
        self.graph.create_edge("water", "temperature", EdgeType.CORRELATES, strength=0.91)
        self.graph.create_edge("temperature", "hot", EdgeType.IS_A, strength=0.95)
        self.graph.create_edge("hot", "burn", EdgeType.CAUSES, strength=0.93)

        paths = self.graph.find_paths("steam", "burn", max_hops=7)
        self.assertGreaterEqual(len(paths), 1)
        top = paths[0]
        self.assertEqual(top.node_labels[0], "steam")
        self.assertEqual(top.node_labels[-1], "burn")
        self.assertEqual(top.hops, 4)
        self.assertGreater(top.mean_strength, 0.9)

    def test_path_consensus_upgrades_to_causes(self) -> None:
        self.graph.create_edge("fire", "heat_a", EdgeType.CORRELATES, strength=0.8)
        self.graph.create_edge("heat_a", "burn", EdgeType.CORRELATES, strength=0.8)
        self.graph.create_edge("fire", "heat_b", EdgeType.CORRELATES, strength=0.8)
        self.graph.create_edge("heat_b", "burn", EdgeType.CORRELATES, strength=0.8)
        self.graph.create_edge("fire", "heat_c", EdgeType.CORRELATES, strength=0.8)
        self.graph.create_edge("heat_c", "burn", EdgeType.CORRELATES, strength=0.8)

        result = self.graph.path_consensus("fire", "burn", cause_threshold=3, auto_upgrade=True)
        self.assertEqual(result.path_count, 3)
        self.assertEqual(result.inferred_type, EdgeType.CAUSES)
        upgraded = self.graph.get_edge("fire", "burn")
        self.assertIsNotNone(upgraded)
        assert upgraded is not None
        self.assertEqual(upgraded.type, EdgeType.CAUSES)

    def test_contradiction_vote_7_vs_1(self) -> None:
        for idx in range(7):
            mid = f"burn_path_{idx}"
            self.graph.create_edge("fire", mid, EdgeType.CORRELATES, strength=0.7)
            self.graph.create_edge(mid, "burn", EdgeType.CAUSES, strength=0.75)

        self.graph.create_edge("fire", "safe_path", EdgeType.CORRELATES, strength=0.6)
        self.graph.create_edge("safe_path", "safe", EdgeType.CORRELATES, strength=0.6)

        result = self.graph.contradiction_vote("fire", "burn", "safe", max_hops=3)
        self.assertEqual(result.positive_paths, 7)
        self.assertEqual(result.negative_paths, 1)
        self.assertEqual(result.verdict, "burn")
        self.assertTrue(math.isclose(result.confidence, 0.875, rel_tol=1e-9))

    def test_contradiction_vote_weakens_minority_edge(self) -> None:
        self.graph.create_edge("fire", "burn", EdgeType.CAUSES, strength=0.8)
        self.graph.create_edge("fire", "burn_alt", EdgeType.CORRELATES, strength=0.8)
        self.graph.create_edge("burn_alt", "burn", EdgeType.CAUSES, strength=0.8)
        minority = self.graph.create_edge("fire", "safe", EdgeType.CORRELATES, strength=0.5)

        result = self.graph.contradiction_vote("fire", "burn", "safe", max_hops=3, weaken_factor=0.5)
        self.assertEqual(result.verdict, "burn")
        self.assertTrue(result.minority_edge_weakened)

        weakened = self.graph.get_edge_by_id(minority.id)
        self.assertIsNotNone(weakened)
        assert weakened is not None
        self.assertLess(weakened.strength, 0.5)

    def test_detect_hubs_returns_high_centrality_nodes(self) -> None:
        self.graph.create_edge("fire", "heat", EdgeType.CAUSES, strength=0.9)
        self.graph.create_edge("steam", "heat", EdgeType.IS_A, strength=0.8)
        self.graph.create_edge("sun", "heat", EdgeType.CAUSES, strength=0.8)
        self.graph.create_edge("heat", "burn", EdgeType.CAUSES, strength=0.9)
        self.graph.create_edge("heat", "temperature", EdgeType.CORRELATES, strength=0.7)

        hubs = self.graph.detect_hubs(limit=5, min_total_degree=3)
        self.assertGreaterEqual(len(hubs), 1)
        labels = [hub.node_label for hub in hubs]
        self.assertIn("heat", labels)
        top = hubs[0]
        self.assertGreaterEqual(top.total_degree, 3)
        self.assertGreater(top.hub_score, 0.0)

    def test_find_analogy_candidates_uses_shared_neighbors(self) -> None:
        self.graph.create_edge("bird", "fly", EdgeType.CAUSES, strength=0.8)
        self.graph.create_edge("bird", "wing", EdgeType.IS_A, strength=0.7)
        self.graph.create_edge("bird", "sky", EdgeType.CORRELATES, strength=0.7)

        self.graph.create_edge("plane", "fly", EdgeType.CAUSES, strength=0.8)
        self.graph.create_edge("plane", "wing", EdgeType.IS_A, strength=0.7)
        self.graph.create_edge("plane", "sky", EdgeType.CORRELATES, strength=0.7)

        analogies = self.graph.find_analogy_candidates("bird", limit=5, min_shared_neighbors=2)
        self.assertGreaterEqual(len(analogies), 1)
        self.assertEqual(analogies[0].candidate_label, "plane")
        self.assertGreaterEqual(analogies[0].shared_count, 2)


if __name__ == "__main__":
    unittest.main()
