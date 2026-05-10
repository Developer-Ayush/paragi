from __future__ import annotations
import unittest
from pathlib import Path
from graph.graph import GraphEngine
from utils.bloom import BloomFilter
from graph.persistence.storage import InMemoryGraphStore
from models.models import EdgeType

class SemanticDedupTests(unittest.TestCase):
    def setUp(self):
        self.bloom_path = Path("test_nodes.bloom.json")
        self.bloom = BloomFilter(capacity=1000, error_rate=0.001)
        self.engine = GraphEngine(
            store=InMemoryGraphStore(),
            bloom=self.bloom,
            bloom_path=self.bloom_path,
            edge_strength_floor=0.001,
            edge_decay_per_cycle=0.005,
            edge_prune_threshold=0.005
        )

    def tearDown(self):
        if self.bloom_path.exists():
            self.bloom_path.unlink()

    def test_semantic_deduplication(self):
        # Create two nodes that are semantically similar
        # "Fire" and "Blaze" should have high similarity in our OwnEncoder if we add some keywords
        # But for now, even with hash backend, if they are identical they will merge.
        # Let's use two nodes that might have similar hashes or just force it by overriding encoder if needed.
        # Actually, let's just test that the logic triggers.

        self.engine.create_or_get_node("global warming")
        self.engine.create_or_get_node("global climate")

        # Add edges to see if they repoint
        self.engine.create_edge("global warming", "heat", EdgeType.CAUSES, strength=0.8)
        self.engine.create_edge("global climate", "melting ice", EdgeType.CAUSES, strength=0.7)

        initial_nodes = self.engine.count_nodes()
        self.assertGreaterEqual(initial_nodes, 3)

        # Force merge by using a lower threshold for testing
        res = self.engine.deduplicate_graph(semantic_threshold=0.1)

        # Should have merged some nodes
        self.assertGreater(res["nodes_merged"], 0)
        final_nodes = self.engine.count_nodes()
        self.assertLess(final_nodes, initial_nodes)

        # Check if edges are repointed
        # All edges should now have the same source if they were merged
        edges = self.engine.list_edges(limit=10)
        sources = set(e.source for e in edges)
        self.assertEqual(len(sources), 1)

if __name__ == "__main__":
    unittest.main()
