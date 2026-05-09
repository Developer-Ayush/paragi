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

    def answer_general(self, *, question: str, domain: str = "general") -> RefineResult:
        query = (question or "").strip()
        if self.backend not in ("ollama", "groq"):
            return RefineResult(
                answer="",
                used=False,
                backend=self.backend,
                model=self.model,
                error="llm_disabled",
                total_duration_ms=None,
            )
        if not query:
            return RefineResult(
                answer="",
                used=False,
                backend=self.backend,
                model=self.model,
                error="empty_question",
                total_duration_ms=None,
            )
        prompt = self._build_general_prompt(question=query, domain=domain)
        text, duration_ms, error = self._generate(prompt, temperature=max(0.1, self.temperature), max_tokens=min(320, max(96, self.max_tokens)))
        if error is not None:
            return RefineResult(
                answer="",
                used=False,
                backend=self.backend,
                model=self.model,
                error=error,
                total_duration_ms=duration_ms,
            )
        out = (text or "").strip()
        if not out:
            return RefineResult(
                answer="",
                used=False,
                backend=self.backend,
                model=self.model,
                error="empty_llm_output",
                total_duration_ms=duration_ms,
            )
        return RefineResult(
            answer=out,
            used=True,
            backend=self.backend,
            model=self.model,
            error=None,
            total_duration_ms=duration_ms,
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
