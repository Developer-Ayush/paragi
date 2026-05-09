from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import List, Set, Dict, Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import trafilatura
from readability import Document
from playwright.sync_api import sync_playwright

from .graph import GraphEngine
from .graph_translator import GraphTranslator
from .models import EdgeType

logger = logging.getLogger(__name__)

class ParagiCrawler:
    def __init__(
        self,
        graph: GraphEngine,
        translator: GraphTranslator,
        rate_limit: float = 1.0
    ) -> None:
        self.graph = graph
        self.translator = translator
        self.rate_limit = rate_limit
        self.last_request_time = 0.0
        self.pages_crawled = 0
        self.queue_size = 0

    def crawl(self, seed_url: str, max_pages: int = 50, max_depth: int = 3) -> None:
        queue = [(seed_url, 0)]
        visited: Set[str] = set()

        while queue and self.pages_crawled < max_pages:
            url, depth = queue.pop(0)
            if depth > max_depth or url in visited or not self._is_allowed(url):
                continue

            visited.add(url)
            # Add to Bloom filter to skip next time
            node_id = f"url:{url}"
            if self.graph.node_exists(node_id):
                continue

            html = self._fetch(url)
            if not html:
                continue

            self.pages_crawled += 1
            self.graph.create_or_get_node(node_id) # Mark as visited in graph

            content = self._extract_content(html)
            logger.info(f"Extracted content length: {len(content) if content else 0}")
            if content:
                self._process_content(content)

            if depth < max_depth:
                links = self._extract_links(html, url)
                for link in links:
                    if link not in visited:
                        queue.append((link, depth + 1))

            self.queue_size = len(queue)

    def crawl_query(self, query: str) -> None:
        urls = self._search(query)
        for url in urls[:5]:
            self.crawl(url, max_pages=1, max_depth=0)

    def _search(self, query: str) -> List[str]:
        # Primary: DuckDuckGo HTML
        urls = self._search_ddg(query)
        if not urls:
            logger.info("DuckDuckGo blocked or empty, falling back to SearXNG")
            urls = self._search_searx(query)
        return urls

    def _search_ddg(self, query: str) -> List[str]:
        url = f"https://html.duckduckgo.com/html/?q={query}"
        html = self._fetch_static(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select("div.result__body a.result__url"):
            href = a.get("href")
            if href:
                # Handle DDG proxy links if necessary, but usually result__url is clean
                links.append(href)
        return links

    def _search_searx(self, query: str) -> List[str]:
        url = f"https://searx.be/search?q={query}&format=json"
        try:
            self._wait_for_rate_limit()
            resp = requests.get(url, timeout=10, headers={"User-Agent": "ParagiCrawler/0.1"})
            self.last_request_time = time.time()
            if resp.status_code == 200:
                data = resp.json()
                return [r["url"] for r in data.get("results", []) if "url" in r]
        except Exception as e:
            logger.error(f"SearXNG search failed: {e}")
        return []

    def _fetch(self, url: str) -> str | None:
        html = self._fetch_static(url)
        if html and self._needs_js(html):
            logger.info(f"Page {url} needs JS, fetching with Playwright")
            html = self._fetch_dynamic(url)
        return html

    def _fetch_static(self, url: str) -> str | None:
        try:
            self._wait_for_rate_limit()
            resp = requests.get(url, timeout=10, headers={"User-Agent": "ParagiCrawler/0.1"})
            self.last_request_time = time.time()

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                time.sleep(retry_after)
                return self._fetch_static(url)

            return resp.text if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"Static fetch failed for {url}: {e}")
            return None

    def _fetch_dynamic(self, url: str) -> str | None:
        try:
            self._wait_for_rate_limit()
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                html = page.content()
                browser.close()
                self.last_request_time = time.time()
                return html
        except Exception as e:
            logger.error(f"Dynamic fetch failed for {url}: {e}")
            return None

    def _needs_js(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if not body:
            return True
        return len(body.get_text(strip=True)) < 500

    def _extract_content(self, html: str) -> str | None:
        content = trafilatura.extract(html)
        if not content:
            doc = Document(html)
            content = doc.summary()
            # Clean summary from HTML tags if needed
            content = BeautifulSoup(content, "html.parser").get_text()

        if not content:
            # Basic regex fallback
            content = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL)
            content = re.sub(r'<style.*?>.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<.*?>', '', content)
            content = re.sub(r'\s+', ' ', content).strip()

        return content

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc
        links = set()

        for a in soup.find_all("a", href=True):
            url = urljoin(base_url, a["href"])
            if urlparse(url).netloc == base_domain:
                # Same domain only
                links.add(url.split("#")[0].rstrip("/"))

        return list(links)

    def _is_allowed(self, url: str) -> bool:
        # Check binary files
        if any(url.lower().endswith(ext) for ext in [".pdf", ".zip", ".jpg", ".jpeg", ".png", ".mp4", ".mp3"]):
            return False

        # Robots.txt check
        try:
            parsed = urlparse(url)
            rp = RobotFileParser()
            rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
            # In a real one we'd cache this.
            rp.read()
            if not rp.can_fetch("ParagiCrawler", url):
                return False
        except Exception:
            pass

        node_id = f"url:{url}"
        if self.graph.node_exists(node_id):
            return False

        return True

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)

    def _process_content(self, content: str) -> None:
        words = content.split()
        chunk_size = 120
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk) < 50:
                continue

            res = self.translator.encode(chunk)
            if res and res.get("confidence", 0) > 0.4:
                source = res["source"]
                target = res["target"]
                rel_type = EdgeType(res["relation"])
                confidence = res["confidence"]

                # Add contradiction detection at ingestion
                # If we're saying A causes B, check if there's evidence A causes NOT B
                # For now, we check if there's a strong path to another target from the same source
                # that might contradict this one. The paper specifically mentioned contradiction
                # detection at ingestion.

                # Simple check: if source and target already have a contradicting edge or path
                # We use contradiction_vote if we can identify a negative target.
                # Since we don't have a 'negative' target from one chunk, we can at least check
                # if the new edge contradicts existing consensus.

                # If relation is CAUSES, check if there are many paths already to something else
                # that would make this cause unlikely.

                # For now, let's implement the 'flagging' part.
                existing_edge = self.graph.get_edge(source, target)
                if existing_edge and existing_edge.strength > 0.7 and rel_type != existing_edge.type:
                    logger.warning(f"Ingestion contradiction: {source} -> {target} is {existing_edge.type} (strength {existing_edge.strength:.2f}), crawler says {rel_type}")
                    # Weaken the new ingestion strength
                    confidence *= 0.5

                self.graph.create_edge(
                    source_label=source,
                    target_label=target,
                    edge_type=rel_type,
                    strength=confidence
                )
