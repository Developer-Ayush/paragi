from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


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
        timeout_seconds: float = 12.0,
        temperature: float = 0.2,
        max_tokens: int = 220,
        seed: int = 42,
        keep_alive: str = "30m",
        api_key: str = "",
    ) -> None:
        self.backend = (backend or "none").strip().lower()
        self.model = (model or "").strip() or "gemma3:4b"
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.timeout_seconds = float(max(1.0, timeout_seconds))
        self.temperature = float(max(0.0, min(1.5, temperature)))
        self.max_tokens = int(max(32, min(1024, max_tokens)))
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
        raw = (base_answer or "").strip()
        if self.backend not in ("ollama", "groq"):
            return RefineResult(
                answer=raw,
                used=False,
                backend=self.backend,
                model=self.model,
                error=None,
                total_duration_ms=None,
            )
        if not raw:
            return RefineResult(
                answer=raw,
                used=False,
                backend=self.backend,
                model=self.model,
                error="empty_base_answer",
                total_duration_ms=None,
            )

        prompt = self._build_prompt(
            question=question,
            base_answer=raw,
            node_path=node_path,
            confidence=confidence,
            scope=scope,
            domain=domain,
            used_fallback=used_fallback,
        )
        text, duration_ms, error = self._generate(prompt, temperature=self.temperature, max_tokens=self.max_tokens)
        if error is not None:
            return RefineResult(
                answer=raw,
                used=False,
                backend=self.backend,
                model=self.model,
                error=error,
                total_duration_ms=duration_ms,
            )
        refined = (text or "").strip()
        if not refined:
            return RefineResult(
                answer=raw,
                used=False,
                backend=self.backend,
                model=self.model,
                error="empty_llm_output",
                total_duration_ms=duration_ms,
            )
        return RefineResult(
            answer=refined,
            used=True,
            backend=self.backend,
            model=self.model,
            error=None,
            total_duration_ms=duration_ms,
        )

    # ── LLM-first pipeline methods ──────────────────────────────────────

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
        # Phase 1 — full query analysis
        query_type: str  # QueryType value
        emotional_tone: str  # neutral, positive, negative, curious, frustrated
        temporal_nature: str  # static, realtime, episodic
        requires_web: bool
        requires_graph: bool
        requires_personal_graph: bool
        requires_reasoning: bool
        requires_fallback: bool
        entities: list[str]
        learnability: float  # 0.0-1.0 how learnable is the stated fact

    def parse_intent(self, question: str) -> "LLMRefiner.ParsedIntent":
        """Step 1: Ask the LLM to understand the user query and extract structured intent."""
        query = (question or "").strip()
        empty = LLMRefiner.ParsedIntent(
            kind="unknown", source=None, target=None, concept=None,
            personal_attribute=None, personal_value=None,
            graph_edges=[], raw_llm="", error=None, duration_ms=None,
            query_type="STATIC_KNOWLEDGE", emotional_tone="neutral",
            temporal_nature="static", requires_web=False, requires_graph=True,
            requires_personal_graph=False, requires_reasoning=False,
            requires_fallback=False, entities=[], learnability=0.0,
        )
        if self.backend not in ("ollama", "groq") or not query:
            empty.error = "llm_disabled" if self.backend not in ("ollama", "groq") else "empty"
            return empty

        prompt = self._build_parse_intent_prompt(query)
        text, duration_ms, error = self._generate(prompt, temperature=0.05, max_tokens=300)
        if error is not None:
            empty.error = error
            empty.duration_ms = duration_ms
            return empty

        raw = (text or "").strip()
        if not raw:
            empty.error = "empty_llm_output"
            empty.duration_ms = duration_ms
            return empty

        return self._parse_intent_json(raw, duration_ms)

    def format_response(
        self,
        *,
        question: str,
        graph_answer: str,
        node_path: list[str],
        confidence: float,
        intent_kind: str,
    ) -> RefineResult:
        """Step 2: Always produce a clean, human-readable final answer."""
        query = (question or "").strip()
        if self.backend not in ("ollama", "groq"):
            # LLM disabled — return graph answer as-is
            return RefineResult(
                answer=graph_answer or "",
                used=False, backend=self.backend, model=self.model,
                error=None, total_duration_ms=None,
            )
        if not query:
            return RefineResult(
                answer=graph_answer or "",
                used=False, backend=self.backend, model=self.model,
                error="empty_question", total_duration_ms=None,
            )

        prompt = self._build_format_response_prompt(
            question=query,
            graph_answer=graph_answer,
            node_path=node_path,
            confidence=confidence,
            intent_kind=intent_kind,
        )
        text, duration_ms, error = self._generate(
            prompt, temperature=0.15, max_tokens=min(400, max(96, self.max_tokens)),
        )
        if error is not None:
            return RefineResult(
                answer=graph_answer or "",
                used=False, backend=self.backend, model=self.model,
                error=error, total_duration_ms=duration_ms,
            )
        out = (text or "").strip()
        if not out:
            return RefineResult(
                answer=graph_answer or "",
                used=False, backend=self.backend, model=self.model,
                error="empty_llm_output", total_duration_ms=duration_ms,
            )
        return RefineResult(
            answer=out, used=True, backend=self.backend, model=self.model,
            error=None, total_duration_ms=duration_ms,
        )

    def _build_parse_intent_prompt(self, question: str) -> str:
        return (
            "You are a query parser for a knowledge graph system.\n"
            "Analyze the user's message and return ONLY valid JSON (no markdown, no explanation).\n\n"
            "Return this exact JSON structure:\n"
            '{\n'
            '  "kind": "relation" | "concept" | "personal_fact" | "personal_query" | "general_fact" | "greeting" | "unknown",\n'
            '  "source": "entity1 or null",\n'
            '  "target": "entity2 or null",\n'
            '  "concept": "main topic or null",\n'
            '  "personal_attribute": "name/location/preference or null",\n'
            '  "personal_value": "the value or null",\n'
            '  "graph_edges": [{"source": "entity1", "target": "entity2", "relation": "IS_A|CAUSES|CORRELATES|TEMPORAL"}],\n'
            '  "query_type": "STATIC_KNOWLEDGE|REALTIME_KNOWLEDGE|PERSONAL_MEMORY|CAUSAL_REASONING|ANALOGICAL_REASONING|EXPLORATORY_REASONING",\n'
            '  "emotional_tone": "neutral|positive|negative|curious|frustrated",\n'
            '  "temporal_nature": "static|realtime|episodic",\n'
            '  "requires_web": false,\n'
            '  "entities": ["entity1", "entity2"],\n'
            '  "learnability": 0.8\n'
            '}\n\n'
            "Rules:\n"
            '- "greeting": for hi, hello, hey, etc.\n'
            '- "relation": for questions like "does X cause Y", "is X related to Y"\n'
            '- "concept": for "what is X", "who is X", "explain X", "how much X", "networth of X", etc.\n'
            '- "personal_fact": for "my name is X", "I am from X", "I like X"\n'
            '- "personal_query": for "what is my name", "who am I", "where do I live"\n'
            '- "general_fact": for "X is Y", "modi is the pm of india" (user teaching a fact)\n'
            '- For concept queries, set "concept" to the main subject\n'
            '- For general_fact, extract graph_edges the system should learn\n'
            '- graph_edges should capture ALL factual relationships stated or implied\n'
            '- query_type REALTIME_KNOWLEDGE for news, weather, stocks, live events, current leaders\n'
            '- learnability: 0.0 for questions, 1.0 for definitive facts, 0.5 for opinions\n'
            '- entities: list ALL named entities mentioned\n\n'
            f"User message: {question}\n"
        )

    def _build_format_response_prompt(
        self, *, question: str, graph_answer: str, node_path: list[str],
        confidence: float, intent_kind: str,
    ) -> str:
        path_text = " -> ".join(node_path) if node_path else "-"
        has_answer = bool(graph_answer and graph_answer.strip() and confidence > 0.05)
        
        if has_answer:
            uncertainty_note = ""
            if confidence < 0.35:
                uncertainty_note = (
                    "IMPORTANT: Memory confidence is LOW. You SHOULD use your own knowledge to verify and "
                    "AUGMENT the answer if the provided memory seems too shallow or slightly incorrect. "
                    "However, do not contradict the memory unless you are certain it is wrong.\n"
                )
            elif confidence < 0.65:
                uncertainty_note = (
                    "Note: Memory confidence is moderate. Use your knowledge to provide a clear, helpful context "
                    "around the provided memory facts.\n"
                )
            
            return (
                "You are the voice of Paragi, an advanced cognition engine. "
                "Rewrite the following answer into clear, natural, high-quality language.\n"
                "Rules:\n"
                "1) Use the provided 'Available information' as the primary source.\n"
                "2) If the provided information is shallow (e.g., just a list of categories), "
                "AUGMENT it with your own general knowledge to make it truly helpful.\n"
                "3) Keep it concise (2-4 sentences).\n"
                "4) Never mention graphs, nodes, paths, confidence, or internal implementation details.\n"
                "5) Return plain text only.\n"
                f"{uncertainty_note}\n"
                f"Question: {question}\n"
                f"Available information: {graph_answer}\n"
                f"Knowledge path: {path_text}\n"
                f"Confidence: {confidence:.3f}\n"
            )
        
        return (
            "You are Paragi, a highly intelligent and concise AI assistant. "
            "The internal knowledge graph did not return a strong match for this query, "
            "so you must answer using your own general knowledge.\n"
            "Rules:\n"
            "1) Answer the question directly and helpfully.\n"
            "2) Keep the response concise (2-5 sentences).\n"
            "3) If you are genuinely unsure about a specific fact, state your uncertainty briefly.\n"
            "4) Do not mention internal systems, graphs, or implementation details.\n"
            "5) Use plain text only.\n\n"
            f"Question: {question}\n"
        )

    def _parse_intent_json(self, raw: str, duration_ms: float | None) -> "LLMRefiner.ParsedIntent":
        """Parse the raw LLM output as JSON, with robust fallback."""
        import re
        # Try to extract JSON from the response (LLMs sometimes wrap in ```json```)
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw, re.DOTALL)
        text_to_parse = json_match.group(0) if json_match else raw
        try:
            data = json.loads(text_to_parse)
        except json.JSONDecodeError:
            return LLMRefiner.ParsedIntent(
                kind="unknown", source=None, target=None, concept=None,
                personal_attribute=None, personal_value=None,
                graph_edges=[], raw_llm=raw, error="json_parse_error",
                duration_ms=duration_ms,
            )

        kind = str(data.get("kind", "unknown")).strip().lower()
        if kind not in ("relation", "concept", "personal_fact", "personal_query", "general_fact", "greeting", "unknown"):
            kind = "unknown"

        edges_raw = data.get("graph_edges", [])
        graph_edges = []
        if isinstance(edges_raw, list):
            for edge in edges_raw:
                if isinstance(edge, dict) and "source" in edge and "target" in edge:
                    graph_edges.append({
                        "source": str(edge["source"]).strip().lower(),
                        "target": str(edge["target"]).strip().lower(),
                        "relation": str(edge.get("relation", "CORRELATES")).strip().upper(),
                    })

        return LLMRefiner.ParsedIntent(
            kind=kind,
            source=str(data.get("source", "")).strip().lower() or None,
            target=str(data.get("target", "")).strip().lower() or None,
            concept=str(data.get("concept", "")).strip().lower() or None,
            personal_attribute=str(data.get("personal_attribute", "")).strip().lower() or None,
            personal_value=str(data.get("personal_value", "")).strip().lower() or None,
            graph_edges=graph_edges,
            raw_llm=raw,
            error=None,
            duration_ms=duration_ms,
            query_type=str(data.get("query_type", "STATIC_KNOWLEDGE")).strip().upper(),
            emotional_tone=str(data.get("emotional_tone", "neutral")).strip().lower(),
            temporal_nature=str(data.get("temporal_nature", "static")).strip().lower(),
            requires_web=bool(data.get("requires_web", False)),
            requires_graph=True,
            requires_personal_graph=kind in ("personal_fact", "personal_query"),
            requires_reasoning=kind in ("relation", "concept"),
            requires_fallback=False,
            entities=[str(e).strip().lower() for e in data.get("entities", []) if isinstance(e, str)],
            learnability=float(data.get("learnability", 0.0)),
        )

    def status(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "backend": self.backend,
            "model": self.model,
            "base_url": self.base_url,
            "enabled": self.backend in ("ollama", "groq"),
            "keep_alive": self.keep_alive,
        }
        if self.backend == "groq":
            payload["reachable"] = bool(self.api_key)
            payload["reason"] = "" if self.api_key else "missing_api_key"
            payload["available_models"] = ["llama3-8b-8192", "llama3-70b-8192", "gemma2-9b-it"]
            payload["model_available"] = True
            return payload

        if self.backend != "ollama":
            payload["reachable"] = False
            payload["reason"] = "disabled"
            return payload

        endpoint = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(endpoint, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(body)
            models = data.get("models", [])
            names: list[str] = []
            if isinstance(models, list):
                for row in models[:40]:
                    if isinstance(row, dict):
                        name = str(row.get("name", "")).strip()
                        if name:
                            names.append(name)
            payload["reachable"] = True
            payload["available_models"] = names
            payload["model_available"] = self.model in set(names)
            return payload
        except Exception as exc:
            payload["reachable"] = False
            payload["reason"] = str(exc)
            return payload

    def _build_prompt(
        self,
        *,
        question: str,
        base_answer: str,
        node_path: list[str],
        confidence: float,
        scope: str,
        domain: str,
        used_fallback: bool,
    ) -> str:
        path_text = " -> ".join(node_path) if node_path else "-"
        return (
            "Rewrite the answer into clear, natural language.\n"
            "Rules:\n"
            "1) Stay faithful to the provided memory answer and path.\n"
            "2) Do not invent extra facts.\n"
            "3) Keep response short (1-3 sentences).\n"
            "4) If confidence is low, include uncertainty naturally.\n"
            "5) Do not mention internal systems, graph, path, confidence, or fallback.\n"
            "6) Return plain text only.\n\n"
            f"Question: {question}\n"
            f"Memory answer: {base_answer}\n"
            f"Memory path: {path_text}\n"
            f"Confidence: {confidence:.3f}\n"
            f"Scope: {scope}\n"
            f"Domain: {domain}\n"
            f"Fallback used: {str(bool(used_fallback)).lower()}\n"
        )

    def _build_general_prompt(self, *, question: str, domain: str) -> str:
        return (
            "You are a concise assistant.\n"
            "Answer the user question clearly in 2-5 sentences.\n"
            "If unsure, say uncertainty briefly.\n"
            "Do not mention internal systems, graphs, or implementation details.\n"
            "Use plain text only.\n\n"
            f"Domain hint: {domain}\n"
            f"Question: {question}\n"
        )

    def _generate(self, prompt: str, *, temperature: float, max_tokens: int) -> tuple[str, float | None, str | None]:
        if self.backend == "groq":
            return self._request_generate_groq(prompt, temperature=temperature, max_tokens=max_tokens)

        text, duration_ms, error, status = self._request_generate(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            include_keep_alive=True,
            include_options=True,
        )
        if error is None:
            return text, duration_ms, None

        if status == 400:
            text2, duration_ms2, error2, status2 = self._request_generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                include_keep_alive=False,
                include_options=True,
            )
            if error2 is None:
                return text2, duration_ms2, None
            if status2 == 400:
                text3, duration_ms3, error3, _status3 = self._request_generate(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    include_keep_alive=False,
                    include_options=False,
                )
                if error3 is None:
                    return text3, duration_ms3, None
                return "", None, error3
            return "", None, error2

        return "", None, error

    def _request_generate(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
        include_keep_alive: bool,
        include_options: bool,
    ) -> tuple[str, float | None, str | None, int | None]:
        endpoint = f"{self.base_url}/api/generate"
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if include_keep_alive:
            body["keep_alive"] = self._coerce_keep_alive(self.keep_alive)
        if include_options:
            body["options"] = {
                "temperature": float(max(0.0, min(1.5, temperature))),
                "num_predict": int(max(32, min(1024, max_tokens))),
                "seed": self.seed,
            }
        encoded = json.dumps(body, ensure_ascii=True).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as exc:
            return "", None, f"http_error:{exc.code}", int(exc.code)
        except urllib.error.URLError as exc:
            return "", None, f"connection_error:{exc.reason}", None
        except TimeoutError:
            return "", None, "timeout", None
        except Exception as exc:
            return "", None, str(exc), None

        text = str(payload.get("response", "")).strip()
        total_duration_ns = payload.get("total_duration")
        duration_ms = None
        try:
            if total_duration_ns is not None:
                duration_ms = float(total_duration_ns) / 1_000_000.0
        except Exception:
            duration_ms = None
        return text, duration_ms, None, None

    @staticmethod
    def _coerce_keep_alive(value: str) -> str | int:
        raw = (value or "").strip()
        if not raw:
            return "30m"
        try:
            if raw.lstrip("-").isdigit():
                return int(raw)
        except Exception:
            pass
        return raw

    def _request_generate_groq(
        self, prompt: str, *, temperature: float, max_tokens: int
    ) -> tuple[str, float | None, str | None]:
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        model = self.model if self.model and self.model != "google/gemma-4-31b-it:free" else "google/gemma-4-26b-a4b-it:free"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(max(0.0, min(1.5, temperature))),
            "max_completion_tokens": int(max(32, min(1024, max_tokens))),
            "stream": False,
        }
        encoded = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=encoded,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            method="POST",
        )
        import time
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        except urllib.error.HTTPError as exc:
            return "", None, f"http_error:{exc.code}"
        except Exception as exc:
            return "", None, str(exc)

        duration_ms = (time.perf_counter() - t0) * 1000.0
        choices = payload.get("choices", [])
        if not choices:
            return "", duration_ms, "no_choices"
        text = str(choices[0].get("message", {}).get("content", "")).strip()
        return text, duration_ms, None
