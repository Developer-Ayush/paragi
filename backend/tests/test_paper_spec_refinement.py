import unittest
from pathlib import Path
import tempfile
import shutil

from app.graph import GraphEngine, VECTOR_SIZE
from app.models import EdgeType, EdgeRecord, normalize_label
from app.bloom import BloomFilter
from app.storage import InMemoryGraphStore

class PaperSpecRefinementTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryGraphStore()
        self.bloom = BloomFilter(capacity=1000, error_rate=0.01)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.bloom_path = self.temp_dir / "test.bloom.json"
        self.engine = GraphEngine(
            store=self.store,
            bloom=self.bloom,
            bloom_path=self.bloom_path,
            edge_strength_floor=0.01,
            edge_decay_per_cycle=0.05
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_strengthen_edge_follows_paper_formula(self):
        # Setup edge with specific vector values for eta and decay_param
        # eta at 850, D at 900
        vector = [0.0] * VECTOR_SIZE
        vector[850] = 0.2  # eta
        vector[900] = 0.1  # decay_param

        edge = self.engine.create_edge(
            "source", "target",
            strength=0.5,
            vector=vector,
            emotional_weight=0.8,
            stability=1.0
        )

        # Initial R (recall_count) is 0
        # Formula: Δstrength = η(S - strength) + αR - βD
        # Δ = 0.2 * (0.8 - 0.5) + 0.01 * 0 - 0.005 * 0.1
        # Δ = 0.2 * 0.3 - 0.0005 = 0.06 - 0.0005 = 0.0595

        # applied_delta = max(0.1, 0.0595) = 0.1 (manual delta default)
        # next_strength = 0.5 + 0.1 = 0.6

        updated = self.engine.strengthen_edge(edge.id)
        self.assertAlmostEqual(updated.strength, 0.6)

        # Now R = 1. Let's make rule_delta > manual_delta (0.1)
        # Increase eta to 0.5
        vector[850] = 0.5
        self.engine.create_edge("source", "target", strength=0.6, vector=vector, emotional_weight=0.8)

        # R = 1
        # Δ = 0.5 * (0.8 - 0.6) + 0.01 * 1 - 0.005 * 0.1
        # Δ = 0.5 * 0.2 + 0.01 - 0.0005 = 0.1 + 0.01 - 0.0005 = 0.1095

        # applied_delta = max(0.1, 0.1095) = 0.1095
        # next_strength = 0.6 + 0.1095 = 0.7095

        updated2 = self.engine.strengthen_edge(edge.id)
        self.assertAlmostEqual(updated2.strength, 0.7095)

    def test_per_dimension_decay(self):
        vector = [1.0] * VECTOR_SIZE
        edge = self.engine.create_edge("source", "target", strength=0.5, vector=vector)

        # Base decay = 0.05
        # Emotional (175-209): rate = 0.05 * 0.1 = 0.005. Expected = 1.0 * (1 - 0.005) = 0.995
        # Factual (580-639): rate = 0.05 * 2.0 = 0.1. Expected = 1.0 * (1 - 0.1) = 0.9
        # Other: rate = 0.05. Expected = 1.0 * (1 - 0.05) = 0.95

        self.engine.decay_all_edges()

        updated = self.engine.get_edge_by_id(edge.id)
        self.assertAlmostEqual(updated.vector[180], 0.995)
        self.assertAlmostEqual(updated.vector[600], 0.9)
        self.assertAlmostEqual(updated.vector[100], 0.95)
        self.assertAlmostEqual(updated.strength, 0.5 * 0.95)

    def test_deduplicate_nodes_merges_identical_labels(self):
        # Create two nodes that should be merged
        # Graph: A -> B, B' -> C where B and B' have same normalized label
        self.engine.create_edge("node a", "node b", strength=0.5)

        # Manually create a node with same normalized label but different original case
        # We need to bypass create_or_get_node's normal behavior to get a duplicate in the store
        # for this test scenario (e.g. if one was created before normalization rules were tight)
        node_b_prime = self.engine.create_or_get_node("NODE B", force_new=True)
        node_c = self.engine.create_or_get_node("node c")
        self.engine.create_edge(node_b_prime.label, node_c.label, strength=0.7)

        # Initially 3 nodes + 1 "node b" normalized
        # "node a", "node b", "NODE B", "node c"
        self.assertEqual(self.engine.count_nodes(), 4)

        stats = self.engine.deduplicate_graph()
        self.assertEqual(stats["nodes_merged"], 1)

        # Now 3 nodes: "node a", "node b" (merged), and "node c"
        self.assertEqual(self.engine.count_nodes(), 3)

        # Check edges
        # Should have a -> b and b -> c
        neighbors_a = self.engine.get_neighbors("node a")
        self.assertEqual(len(neighbors_a), 1)

        b_label = self.engine.get_node_label(neighbors_a[0].target)
        self.assertEqual(normalize_label(b_label), "node b")

        neighbors_b = self.engine.get_neighbors(b_label)
        self.assertEqual(len(neighbors_b), 1)
        self.assertEqual(normalize_label(self.engine.get_node_label(neighbors_b[0].target)), "node c")

if __name__ == "__main__":
    unittest.main()
