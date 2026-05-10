from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from .models import EdgeType, normalize_label


@dataclass(slots=True)
class RelationCandidate:
    source: str
    target: str
    edge_type: EdgeType
    strength: float
    source_name: str


class ExternalKnowledgeConnector(ABC):
    name: str

    @abstractmethod
    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 1.5) -> List[RelationCandidate]:
        raise NotImplementedError

    def fetch_concept(self, concept: str, timeout_seconds: float = 1.5) -> List[RelationCandidate]:
        return []


class ConceptNetConnector(ExternalKnowledgeConnector):
    name = "conceptnet"
    endpoint = "https://api.conceptnet.io/query"

    relation_map = {
        "/r/Causes": EdgeType.CAUSES,
        "/r/IsA": EdgeType.IS_A,
        "/r/RelatedTo": EdgeType.CORRELATES,
        "/r/HasProperty": EdgeType.CORRELATES,
        "/r/PartOf": EdgeType.CORRELATES,
        "/r/UsedFor": EdgeType.CORRELATES,
        "/r/HasSubevent": EdgeType.TEMPORAL,
    }

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 1.5) -> List[RelationCandidate]:
        source = normalize_label(source)
        target = normalize_label(target)
        params = {
            "node": f"/c/en/{source.replace(' ', '_')}",
            "other": f"/c/en/{target.replace(' ', '_')}",
            "limit": "10",
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        edges = payload.get("edges", [])
        candidates: list[RelationCandidate] = []
        for edge in edges:
            rel_id = edge.get("rel", {}).get("@id")
            edge_type = self.relation_map.get(rel_id, EdgeType.CORRELATES)

            start_label = normalize_label(str(edge.get("start", {}).get("label", source)))
            end_label = normalize_label(str(edge.get("end", {}).get("label", target)))
            weight = float(edge.get("weight", 1.0))
            strength = min(0.95, max(0.35, 0.5 + (weight / 10.0)))

            if source == start_label and target == end_label:
                candidates.append(
                    RelationCandidate(
                        source=source,
                        target=target,
                        edge_type=edge_type,
                        strength=strength,
                        source_name=self.name,
                    )
                )
            elif source == end_label and target == start_label:
                # If reverse exists, still keep weak inferred direction.
                candidates.append(
                    RelationCandidate(
                        source=source,
                        target=target,
                        edge_type=EdgeType.CORRELATES,
                        strength=max(0.35, strength * 0.75),
                        source_name=self.name,
                    )
                )

        return candidates


class SemanticScholarConnector(ExternalKnowledgeConnector):
    name = "semanticscholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 1.5) -> List[RelationCandidate]:
        source = normalize_label(source)
        target = normalize_label(target)
        query = f"{source} {target}"
        params = {
            "query": query,
            "limit": "3",
            "fields": "title,abstract",
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        papers = payload.get("data", [])
        if not isinstance(papers, list):
            return []

        for paper in papers:
            title = normalize_label(str(paper.get("title", "")))
            abstract = normalize_label(str(paper.get("abstract", "")))
            blob = f"{title} {abstract}"
            if source in blob and target in blob:
                return [
                    RelationCandidate(
                        source=source,
                        target=target,
                        edge_type=EdgeType.CORRELATES,
                        strength=0.68,
                        source_name=self.name,
                    )
                ]
        return []


class PubMedConnector(ExternalKnowledgeConnector):
    name = "pubmed"
    endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 2.0) -> List[RelationCandidate]:
        source = normalize_label(source)
        target = normalize_label(target)
        query = f"{source}[mesh] AND {target}[mesh]"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": "5",
            "retmode": "json",
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))

            ids = payload.get("esearchresult", {}).get("idlist", [])
            if ids:
                return [RelationCandidate(
                    source=source, target=target,
                    edge_type=EdgeType.CORRELATES,
                    strength=0.75,
                    source_name=self.name
                )]
        except Exception:
            pass
        return []

class ArxivConnector(ExternalKnowledgeConnector):
    name = "arxiv"
    endpoint = "http://export.arxiv.org/api/query"

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 2.0) -> List[RelationCandidate]:
        source = normalize_label(source)
        target = normalize_label(target)
        query = f"all:{source} AND all:{target}"
        params = {
            "search_query": query,
            "max_results": "3",
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                # Arxiv returns XML, just check if source and target are in the response
                content = resp.read().decode("utf-8").lower()
                if source in content and target in content:
                    return [RelationCandidate(
                        source=source, target=target,
                        edge_type=EdgeType.CORRELATES,
                        strength=0.70,
                        source_name=self.name
                    )]
        except Exception:
            pass
        return []

class CourtListenerConnector(ExternalKnowledgeConnector):
    name = "courtlistener"
    endpoint = "https://www.courtlistener.com/api/rest/v3/search/"

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 2.0) -> List[RelationCandidate]:
        source = normalize_label(source)
        target = normalize_label(target)
        query = f'"{source}" AND "{target}"'
        params = {
            "q": query,
        }
        url = self.endpoint + "?" + urllib.parse.urlencode(params)
        try:
            # Requires token usually, but some search might be public or mocked for now
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                if payload.get("count", 0) > 0:
                    return [RelationCandidate(
                        source=source, target=target,
                        edge_type=EdgeType.IS_A, # Legal often defines things
                        strength=0.65,
                        source_name=self.name
                    )]
        except Exception:
            pass
        return []

class NewsRSSConnector(ExternalKnowledgeConnector):
    name = "news_rss"
    feeds = [
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "http://feeds.bbci.co.uk/news/rss.xml"
    ]

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 2.0) -> List[RelationCandidate]:
        # Implementation would fetch feeds and look for co-occurrence
        # Mocking for now to show structure
        return []


class WikipediaConnector(ExternalKnowledgeConnector):
    name = "wikipedia"
    endpoint = "https://en.wikipedia.org/api/rest_v1/page/summary/"

    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "into",
        "about",
        "which",
        "their",
        "there",
        "have",
        "has",
        "are",
        "was",
        "were",
        "been",
        "being",
        "than",
        "then",
        "when",
        "where",
        "what",
        "who",
        "how",
        "why",
        "can",
        "could",
        "will",
        "would",
        "should",
        "also",
        "such",
        "other",
        "most",
        "more",
        "many",
        "some",
        "used",
        "using",
        "use",
        "between",
        "through",
        "each",
        "both",
        "over",
        "under",
    }
    _token_re = re.compile(r"[a-z][a-z']{2,}")
    _noise_tokens = {
        "also",
        "called",
        "known",
        "term",
        "thing",
        "things",
        "system",
        "systems",
        "processes",
        "method",
        "methods",
        "type",
        "types",
        "include",
        "includes",
        "including",
        "based",
        "bearing",
    }

    def fetch_relation(self, source: str, target: str, timeout_seconds: float = 1.5) -> List[RelationCandidate]:
        source = normalize_label(source)
        target = normalize_label(target)
        
        # Step 1: Search for the best page title
        best_title = self._search_title(source, timeout_seconds=timeout_seconds * 0.4)
        if not best_title:
            best_title = source.replace(" ", "_")
        
        page = urllib.parse.quote(best_title)
        url = self.endpoint + page
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds * 0.6) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        extract = normalize_label(str(payload.get("extract", "")))
        if not extract:
            return []

        if target in extract:
            return [
                RelationCandidate(
                    source=source,
                    target=target,
                    edge_type=EdgeType.CORRELATES,
                    strength=0.62,
                    source_name=self.name,
                )
            ]
        return []

    def _search_title(self, query: str, timeout_seconds: float) -> str | None:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&limit=1"
        try:
            req = urllib.request.Request(search_url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("query", {}).get("search", [])
                if results:
                    return results[0].get("title")
        except Exception:
            pass
        return None

    def fetch_concept(self, concept: str, timeout_seconds: float = 1.5) -> List[RelationCandidate]:
        source = normalize_label(concept)
        
        # Step 1: Search for best title
        best_title = self._search_title(source, timeout_seconds=timeout_seconds * 0.4)
        if not best_title:
            best_title = source.replace(" ", "_")

        page = urllib.parse.quote(best_title)
        url = self.endpoint + page
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "paragi-prototype/0.3"})
            with urllib.request.urlopen(req, timeout=timeout_seconds * 0.6) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return []

        extract_raw = str(payload.get("extract", "")).strip()
        extract = normalize_label(extract_raw)
        if not extract_raw or not extract:
            return []

        first_sentence = extract_raw.split(".", 1)[0].strip().lower()
        source_tokens = set(source.split())
        candidates: list[RelationCandidate] = []

        type_target = self._infer_is_a_target(first_sentence, source_tokens)
        if type_target:
            candidates.append(
                RelationCandidate(
                    source=source,
                    target=type_target,
                    edge_type=EdgeType.IS_A,
                    strength=0.72,
                    source_name=self.name,
                )
            )

        tokens = self._token_re.findall(extract.lower())
        source_tokens = set(source.split())
        targets: list[str] = []
        for token in tokens:
            if token in source_tokens:
                continue
            if token in self.stopwords or token in self._noise_tokens:
                continue
            if token.endswith("'s"):
                token = token[:-2]
            if token not in targets:
                targets.append(token)
            if len(targets) >= 4:
                break

        for target in targets:
            if type_target and target == type_target:
                continue
            candidates.append(
                RelationCandidate(
                    source=source,
                    target=target,
                    edge_type=EdgeType.CORRELATES,
                    strength=0.58,
                    source_name=self.name,
                )
            )
        return candidates

    def _infer_is_a_target(self, first_sentence: str, source_tokens: set[str]) -> str:
        if not first_sentence:
            return ""
        match = re.search(r"\bis\s+(?:an?|the)\s+([a-z][a-z ]{1,80})", first_sentence)
        if not match:
            return ""
        phrase = match.group(1).split(",", 1)[0].strip()
        words = self._token_re.findall(phrase)
        if not words:
            return ""
        # Prefer the last meaningful token in the phrase; often the head noun.
        for token in reversed(words):
            if token in self.stopwords or token in self._noise_tokens:
                continue
            if token in source_tokens:
                continue
            return token
        return ""
