from __future__ import annotations

import json
import urllib.error
import urllib.request
import re
from dataclasses import dataclass, field
from typing import Any, List, Dict
import time

from core.constants import VECTOR_SIZE, SEMANTIC_DIMS

@dataclass(slots=True)
class RefineResult:
    answer: str
    used: bool
    backend: str
    model: str
    error: str | None
    total_duration_ms: float | None

class LLMRefiner:
    def __init__(
        self,
        *,
        backend: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 45.0,
        temperature: float = 0.2,
        max_tokens: int = 500,
        seed: int = 42,
        keep_alive: str = "30m",
        api_key: str = "",
    ) -> None:
        self.backend = (backend or "none").strip().lower()
        self.model = (model or "").strip() or "google/gemini-2.0-flash-lite-preview-02-05:free"
        self.base_url = (base_url or "https://openrouter.ai").rstrip("/")
        if not self.base_url.endswith("/api/v1"):
            self.base_url += "/api/v1"
        self.timeout_seconds = float(max(1.0, timeout_seconds))
        self.temperature = float(max(0.0, min(1.5, temperature)))
        self.max_tokens = int(max(32, min(2048, max_tokens)))
        self.seed = int(seed)
        self.keep_alive = (keep_alive or "30m").strip() or "30m"
        self.api_key = (api_key or "").strip()

    def refine_answer(
        self,
        *,
        question: str,
        base_answer: str,
        node_path: list[str],
        confidence: float,
        scope: str,
        domain: str,
        used_fallback: bool,
    ) -> RefineResult:
        return self.format_response(
            question=question,
            graph_answer=base_answer,
            node_path=node_path,
            confidence=confidence,
            intent_kind="general"
        )

    @dataclass(slots=True)
    class ParsedIntent:
        kind: str
        source: str | None
        target: str | None
        concept: str | None
        personal_attribute: str | None
        personal_value: str | None
        graph_edges: list[dict]
        raw_llm: str
        error: str | None
        duration_ms: float | None
        query_type: str
        emotional_tone: str
        temporal_nature: str
        requires_web: bool
        requires_graph: bool
        requires_personal_graph: bool
        requires_reasoning: bool
        requires_fallback: bool
        entities: list[str]
        concepts: list[str] = field(default_factory=list)
        learnability: float = 0.0

    def parse_intent(self, question: str) -> "LLMRefiner.ParsedIntent":
        query = (question or "").strip()
        empty = LLMRefiner.ParsedIntent(
            kind="unknown", source=None, target=None, concept=None,
            personal_attribute=None, personal_value=None,
            graph_edges=[], raw_llm="", error=None, duration_ms=None,
            query_type="STATIC_KNOWLEDGE", emotional_tone="neutral",
            temporal_nature="static", requires_web=False, requires_graph=True,
            requires_personal_graph=False, requires_reasoning=False,
            requires_fallback=False, entities=[], concepts=[], learnability=0.0,
        )
        if not query:
            empty.error = "empty"
            return empty

        prompt = self._build_parse_intent_prompt(query)
        text, duration_ms, error = self._generate(prompt, temperature=0.1, max_tokens=1000)
        if error is not None:
            empty.error = error
            empty.duration_ms = duration_ms
            return empty

        return self._parse_intent_json(text, duration_ms)

    def format_response(
        self,
        *,
        question: str,
        graph_answer: str,
        node_path: list[str],
        confidence: float,
        intent_kind: str,
    ) -> RefineResult:
        query = (question or "").strip()
        prompt = self._build_format_response_prompt(
            question=query,
            graph_answer=graph_answer,
            node_path=node_path,
            confidence=confidence,
            intent_kind=intent_kind,
        )
        text, duration_ms, error = self._generate(
            prompt, temperature=0.3, max_tokens=1000,
        )
        if error is not None:
            return RefineResult(
                answer=graph_answer or "Cognitive pipeline failed to generate response.",
                used=False, backend=self.backend, model=self.model,
                error=error, total_duration_ms=duration_ms,
            )
        return RefineResult(
            answer=text.strip(), used=True, backend=self.backend, model=self.model,
            error=None, total_duration_ms=duration_ms,
        )

    def digest_into_graph(self, text: str) -> list[dict]:
        content = (text or "").strip()
        if not content: return []

        prompt = (
            "You are a knowledge extraction engine for Paragi AGI. Extract factual relationships and cognitive factors.\n"
            "Return a list of edges as JSON:\n"
            '{\n'
            '  "edges": [\n'
            '    {\n'
            '      "source": "entity1",\n'
            '      "target": "entity2",\n'
            '      "relation": "CAUSES|CORRELATES|IS_A|TEMPORAL|PART_OF|ANALOGY",\n'
            '      "vector": [float32[1024]] // Optional: estimation of the 1024-dim vector if possible, otherwise omit\n'
            '    }\n'
            '  ]\n'
            '}\n'
            f"Text: {content}\n"
        )
        out, _, error = self._generate(prompt, temperature=0.0, max_tokens=1000)
        if error or not out: return []

        try:
            match = re.search(r'\{.*\}', out, re.DOTALL)
            data = json.loads(match.group(0))
            return data.get("edges", [])
        except:
            return []

    def _build_parse_intent_prompt(self, question: str) -> str:
        return (
            "You are the Primary Encoder for Paragi, a Graph-based AGI.\n"
            "Analyze the user message and return a structured JSON response.\n\n"
            "JSON STRUCTURE:\n"
            '{\n'
            '  "kind": "relation|concept|personal_fact|personal_query|general_fact|greeting|unknown",\n'
            '  "entities": ["list", "of", "named", "entities"],\n'
            '  "concepts": ["list", "of", "abstract", "concepts"],\n'
            '  "graph_edges": [\n'
            '    {"source": "a", "target": "b", "relation": "CAUSES|CORRELATES|IS_A|TEMPORAL|PART_OF|ANALOGY", "confidence": 0.9}\n'
            '  ],\n'
            '  "requires_web": boolean,\n'
            '  "query_type": "STATIC_KNOWLEDGE|REALTIME_KNOWLEDGE|PERSONAL_MEMORY|CAUSAL_REASONING",\n'
            '  "emotional_tone": "neutral|positive|negative|curious",\n'
            '  "learnability": 0.0 to 1.0\n'
            '}\n\n'
            f"User message: {question}\n"
        )

    def _build_format_response_prompt(
        self, *, question: str, graph_answer: str, node_path: list[str],
        confidence: float, intent_kind: str,
    ) -> str:
        return (
            "You are Paragi, a Continuous Learning AGI.\n"
            "Generate a sleek, intelligent response based on the provided graph facts and your own knowledge.\n\n"
            f"Question: {question}\n"
            f"Graph Facts: {graph_answer}\n"
            f"Reasoning Path: {' -> '.join(node_path) if node_path else 'None'}\n"
            f"Confidence: {confidence}\n"
            "\n"
            "Rules:\n"
            "1. Be concise but insightful.\n"
            "2. Do not mention 'nodes' or 'graphs' directly.\n"
            "3. If graph facts are missing, use your general knowledge but maintain the Paragi persona.\n"
        )

    def _generate(self, prompt: str, *, temperature: float, max_tokens: int) -> tuple[str, float | None, str | None]:
        endpoint = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                duration_ms = (time.perf_counter() - t0) * 1000.0
                text = payload["choices"][0]["message"]["content"]
                return text, duration_ms, None
        except Exception as e:
            return "", None, str(e)

    def _parse_intent_json(self, raw: str, duration_ms: float | None) -> "LLMRefiner.ParsedIntent":
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            data = json.loads(match.group(0))
            return LLMRefiner.ParsedIntent(
                kind=data.get("kind", "unknown"),
                source=data.get("source"),
                target=data.get("target"),
                concept=data.get("concept"),
                personal_attribute=data.get("personal_attribute"),
                personal_value=data.get("personal_value"),
                graph_edges=data.get("graph_edges", []),
                raw_llm=raw,
                error=None,
                duration_ms=duration_ms,
                query_type=data.get("query_type", "STATIC_KNOWLEDGE"),
                emotional_tone=data.get("emotional_tone", "neutral"),
                temporal_nature=data.get("temporal_nature", "static"),
                requires_web=data.get("requires_web", False),
                requires_graph=True,
                requires_personal_graph=data.get("kind") in ("personal_fact", "personal_query"),
                requires_reasoning=True,
                requires_fallback=False,
                entities=data.get("entities", []),
                concepts=data.get("concepts", []),
                learnability=data.get("learnability", 0.0)
            )
        except Exception as e:
            return LLMRefiner.ParsedIntent(
                kind="unknown", source=None, target=None, concept=None,
                personal_attribute=None, personal_value=None,
                graph_edges=[], raw_llm=raw, error=str(e), duration_ms=duration_ms,
                query_type="STATIC_KNOWLEDGE", emotional_tone="neutral",
                temporal_nature="static", requires_web=False, requires_graph=True,
                requires_personal_graph=False, requires_reasoning=False,
                requires_fallback=False, entities=[], concepts=[], learnability=0.0,
            )
