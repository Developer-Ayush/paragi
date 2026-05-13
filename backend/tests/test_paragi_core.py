import unittest
from graph.graph import CognitiveGraph
from graph.graph_store import InMemoryGraphStore
from core.enums import EdgeType

class TestParagiCore(unittest.TestCase):
    def test_graph_initialization(self):
        store = InMemoryGraphStore()
        graph = CognitiveGraph(store)
        self.assertIsNotNone(graph)
