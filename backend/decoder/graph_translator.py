from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import ollama
except ImportError:
    ollama = None
import spacy
from core.enums import EdgeType

logger = logging.getLogger(__name__)

class GraphTranslator:
    def __init__(self, model_name: str = "phi3", data_dir: Path | None = None) -> None:
        self.model_name = model_name
        self.data_dir = data_dir or Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.encoder_log_path = self.data_dir / "encoder_training_log.jsonl"
        self.decoder_log_path = self.data_dir / "decoder_training_log.jsonl"

        self.nlp = None
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            try:
                from spacy.cli import download
                download("en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning(f"Failed to load or download spaCy model: {e}")

        self.valid_relations = [e.value for e in EdgeType]

    def _call_ollama(self, prompt: str, system: str, format: str = "") -> str | None:
        if ollama is None:
            logger.error("Ollama library not installed.")
            return None
        try:
            options = {"temperature": 0.0}
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                system=system,
                format=format,
                options=options
            )
            return response.get("response")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return None

    def encode(self, text: str) -> dict[str, Any]:
        system_prompt = (
            "You are a graph translator. Extract a single relationship from the input text. "
            "Respond ONLY with a JSON object containing keys: source, relation, target, confidence. "
            f"Relation MUST be one of: {', '.join(self.valid_relations)}. "
            "Confidence is a float between 0.0 and 1.0."
        )

        result = None
        fallback_used = False

        ollama_response = self._call_ollama(text, system_prompt, format="json")
        if ollama_response:
            try:
                result = json.loads(ollama_response)
                if not all(k in result for k in ("source", "relation", "target", "confidence")):
                    result = None
                elif result["relation"] not in self.valid_relations:
                    result["relation"] = "INFERRED"
            except Exception:
                result = None

        if result is None:
            fallback_used = True
            result = self._encode_fallback(text)

        # Log for future fine-tuning
        self._log_pair(self.encoder_log_path, {"input": text, "output": result, "fallback": fallback_used})

        result["fallback_used"] = fallback_used
        return result

    def _encode_fallback(self, text: str) -> dict[str, Any]:
        # Basic regex + spaCy fallback
        source, relation, target = "unknown", "INFERRED", "unknown"
        confidence = 0.3

        if self.nlp:
            doc = self.nlp(text)
            nouns = [chunk.text for chunk in doc.noun_chunks]
            if len(nouns) >= 2:
                source = nouns[0]
                target = nouns[1]
                confidence = 0.4

            # Simple relation detection
            text_lower = text.lower()
            if "cause" in text_lower or "lead to" in text_lower:
                relation = "CAUSES"
            elif "is a" in text_lower or "type of" in text_lower:
                relation = "IS_A"
            elif "before" in text_lower or "after" in text_lower:
                relation = "TEMPORAL"
            elif "related" in text_lower or "associate" in text_lower:
                relation = "CORRELATES"

        return {"source": source, "relation": relation, "target": target, "confidence": confidence}

    def decode(self, path: list[dict[str, Any]], confidence: float) -> tuple[str, bool]:
        if not path:
            return "", False

        system_prompt = (
            "You are a graph-to-text decoder. Convert the provided graph path into a natural language sentence. "
            "Do not mention graph nodes or edges. Just state the information naturally."
        )
        path_str = json.dumps(path)
        prompt = f"Path: {path_str}\nOverall confidence: {confidence}"

        result = self._call_ollama(prompt, system_prompt)
        fallback_used = False

        if not result:
            fallback_used = True
            result = self._decode_fallback(path)

        # Log for future fine-tuning
        self._log_pair(self.decoder_log_path, {"path": path, "output": result, "fallback": fallback_used})

        return result, fallback_used

    def _decode_fallback(self, path: list[dict[str, Any]]) -> str:
        clauses = []
        for edge in path:
            s, r, t = edge.get("source"), edge.get("relation"), edge.get("target")
            if r == "CAUSES":
                clauses.append(f"{s} causes {t}")
            elif r == "IS_A":
                clauses.append(f"{s} is a {t}")
            elif r == "TEMPORAL":
                clauses.append(f"{s} happens relative to {t}")
            elif r == "CORRELATES":
                clauses.append(f"{s} is associated with {t}")
            else:
                clauses.append(f"{s} is linked to {t}")

        if not clauses:
            return "No information found."

        if len(clauses) == 1:
            return clauses[0].capitalize() + "."

        return " and ".join(clauses).capitalize() + "."

    def _log_pair(self, path: Path, data: dict[str, Any]) -> None:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps({**data, "timestamp": time.time()}) + "\n")
        except Exception as e:
            logger.error(f"Failed to log to {path}: {e}")
