import unittest
import os
from pathlib import Path
from graph.persistence.hdf5_store import HDF5GraphStore

class TestHDF5GraphStore(unittest.TestCase):
    def setUp(self):
        self.test_h5 = Path("test_graph.h5")
        if self.test_h5.exists():
            os.remove(self.test_h5)
        self.store = HDF5GraphStore(self.test_h5)

    def tearDown(self):
        self.store.close()
        if self.test_h5.exists():
            os.remove(self.test_h5)

    def test_upsert_list_node(self):
        node = {"id": "n1", "label": "test", "type": "CONCEPT"}
        self.store.upsert_node(node)
        nodes = self.store.list_nodes()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["id"], "n1")

    def test_delete_node(self):
        node = {"id": "n1", "label": "test", "type": "CONCEPT"}
        self.store.upsert_node(node)
        self.store.delete_node("n1")
        nodes = self.store.list_nodes()
        self.assertEqual(len(nodes), 0)

    def test_upsert_list_edge(self):
        edge = {"source": "n1", "target": "n2", "type": "CORRELATES", "vector": [0.1, 0.2]}
        self.store.upsert_edge(edge)
        edges = self.store.list_edges()
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["source"], "n1")

    def test_delete_edge(self):
        edge = {"source": "n1", "target": "n2", "type": "CORRELATES"}
        self.store.upsert_edge(edge)
        self.store.delete_edge("n1", "n2")
        edges = self.store.list_edges()
        self.assertEqual(len(edges), 0)

if __name__ == "__main__":
    unittest.main()
