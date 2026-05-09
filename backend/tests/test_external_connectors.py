import unittest
from app.external_sources import PubMedConnector, ArxivConnector, CourtListenerConnector

class TestExternalConnectors(unittest.TestCase):
    def test_pubmed_connector_exists(self):
        connector = PubMedConnector()
        self.assertEqual(connector.name, "pubmed")

    def test_arxiv_connector_exists(self):
        connector = ArxivConnector()
        self.assertEqual(connector.name, "arxiv")

    def test_courtlistener_connector_exists(self):
        connector = CourtListenerConnector()
        self.assertEqual(connector.name, "courtlistener")

if __name__ == "__main__":
    unittest.main()
