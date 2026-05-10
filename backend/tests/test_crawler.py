from __future__ import annotations

import os
import shutil
import unittest
import uuid
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.crawler import ParagiCrawler
from graph.graph import GraphEngine
from decoder.graph_translator import GraphTranslator
from utils.bloom import BloomFilter
from graph.persistence.storage import InMemoryGraphStore

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

class CrawlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"crawler_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)

        self.graph = GraphEngine(
            store=InMemoryGraphStore(),
            bloom=BloomFilter(capacity=1000, error_rate=0.01),
            bloom_path=self.case_dir / "nodes.bloom.json",
            edge_strength_floor=0.001,
            edge_decay_per_cycle=0.005
        )
        self.translator = MagicMock(spec=GraphTranslator)
        self.crawler = ParagiCrawler(self.graph, self.translator, rate_limit=0.1)

    def tearDown(self) -> None:
        self.graph.close()
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_needs_js_detects_near_empty_bodies(self) -> None:
        html_empty = "<html><body></body></html>"
        self.assertTrue(self.crawler._needs_js(html_empty))

        html_full = "<html><body>" + "content " * 100 + "</body></html>"
        self.assertFalse(self.crawler._needs_js(html_full))

    def test_is_allowed_blocks_binary_files(self) -> None:
        self.assertFalse(self.crawler._is_allowed("https://example.com/file.pdf"))
        self.assertFalse(self.crawler._is_allowed("https://example.com/image.jpg"))
        self.assertTrue(self.crawler._is_allowed("https://example.com/page.html"))

    def test_extract_links_same_domain_only(self) -> None:
        html = """
        <a href="/page1">Internal</a>
        <a href="https://example.com/page2">Absolute Internal</a>
        <a href="https://other.com/page3">External</a>
        """
        links = self.crawler._extract_links(html, "https://example.com/")
        self.assertIn("https://example.com/page1", links)
        self.assertIn("https://example.com/page2", links)
        self.assertNotIn("https://other.com/page3", links)

    def test_already_crawled_urls_skipped(self) -> None:
        url = "https://example.com/already"
        self.graph.create_or_get_node(f"url:{url}")
        self.assertFalse(self.crawler._is_allowed(url))

    def test_rate_limiting_respected(self) -> None:
        self.crawler.rate_limit = 0.5
        start = time.time()
        self.crawler._wait_for_rate_limit() # first one should be fast
        self.crawler.last_request_time = time.time()
        self.crawler._wait_for_rate_limit() # second one should wait
        end = time.time()
        self.assertGreaterEqual(end - start, 0.4)

    @patch("urllib.robotparser.RobotFileParser.read")
    @patch("urllib.robotparser.RobotFileParser.can_fetch")
    def test_respects_robots_txt(self, mock_can_fetch, mock_read) -> None:
        url = "https://example.com/blocked"
        mock_can_fetch.return_value = False
        self.assertFalse(self.crawler._is_allowed(url))
        mock_can_fetch.assert_called_with("ParagiCrawler", url)

    @patch("requests.get")
    def test_ddg_fallback_to_searx(self, mock_get) -> None:
        # Mock DDG returning empty
        mock_get.side_effect = [
            MagicMock(status_code=200, text="<html><body>No results</body></html>"),
            MagicMock(status_code=200, json=lambda: {"results": [{"url": "https://searx.com/1"}]})
        ]
        urls = self.crawler._search("test query")
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], "https://searx.com/1")

    def test_process_content_creates_edges(self) -> None:
        self.translator.encode.return_value = {
            "source": "A", "relation": "CAUSES", "target": "B", "confidence": 0.8
        }
        content = "word " * 150 # trigger at least one chunk
        self.crawler._process_content(content)
        self.assertTrue(self.graph.node_exists("A"))
        self.assertTrue(self.graph.node_exists("B"))
        edge = self.graph.get_edge("A", "B")
        self.assertIsNotNone(edge)
        self.assertEqual(edge.type.value, "CAUSES")

    @patch("utils.crawler.ParagiCrawler._fetch")
    @patch("utils.crawler.ParagiCrawler._extract_content")
    def test_crawl_loop(self, mock_extract, mock_fetch) -> None:
        mock_fetch.return_value = "<html><body>Some content</body></html>"
        # Content must be long enough to pass chunk filter in _process_content
        mock_extract.return_value = "word " * 150
        self.translator.encode.return_value = {
            "source": "X", "relation": "IS_A", "target": "Y", "confidence": 0.9, "fallback_used": False
        }

        self.crawler.crawl("https://example.com/start", max_pages=1)
        self.assertEqual(self.crawler.pages_crawled, 1)
        self.assertTrue(self.graph.node_exists("X"))

    @patch("utils.crawler.ParagiCrawler._search")
    @patch("utils.crawler.ParagiCrawler.crawl")
    def test_crawl_query(self, mock_crawl, mock_search) -> None:
        mock_search.return_value = ["url1", "url2", "url3", "url4", "url5", "url6"]
        self.crawler.crawl_query("some query")
        self.assertEqual(mock_crawl.call_count, 5)
        mock_crawl.assert_any_call("url1", max_pages=1, max_depth=0)

if __name__ == "__main__":
    unittest.main()
