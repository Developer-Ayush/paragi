from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List

from .graph import PathMatch
from .models import EdgeType


class OwnDecoder:
    backend = "own"

    default_relation_phrases: dict[EdgeType, list[str]] = {
        EdgeType.CAUSES: ["can cause"],
        EdgeType.CORRELATES: ["is associated with"],
        EdgeType.IS_A: ["is a type of"],
        EdgeType.TEMPORAL: ["usually happens before"],
        EdgeType.INFERRED: ["is likely related to"],
    }

    def __init__(self, *, model_path: Path | None = None) -> None:
        self.model_path = model_path
        self.low_confidence_threshold = 0.12
        self.medium_confidence_threshold = 0.25
        self._relation_phrases: dict[EdgeType, list[str]] = {
            key: list(values) for key, values in self.default_relation_phrases.items()
        }
        if model_path is not None:
            self._load_model(model_path)

    def decode_path(self, path: PathMatch) -> str:
        if path.hops == 0 or len(path.node_labels) < 2:
            return "I do not have enough reliable memory yet to answer this."

        if path.hops == 1:
            strength = path.edge_strengths[0] if path.edge_strengths else 0.0
            return self._single_relation_sentence(
                source=path.node_labels[0],
                target=path.node_labels[1],
                edge_type=path.edge_types[0],
                strength=strength,
            )

        clauses: list[str] = []
        for idx, edge_type in enumerate(path.edge_types):
            source = path.node_labels[idx]
            target = path.node_labels[idx + 1]
            phrase = self._relation_phrase(edge_type)
            clauses.append(f"{source} {phrase} {target}")

        if len(clauses) == 2:
            return f"{clauses[0].capitalize()}, and {clauses[1]}."
        return f"{clauses[0].capitalize()}, then {', then '.join(clauses[1:])}. This is why {path.node_labels[0]} links to {path.node_labels[-1]}."

    def decode_concept(self, concept: str, neighbors: Iterable[tuple[str, EdgeType, float]]) -> str:
        items = list(neighbors)
        if not items:
            return f"I do not have enough reliable information about {concept} yet."

        primary_target, primary_type, primary_strength = items[0]
        primary = self._single_relation_sentence(
            source=concept,
            target=primary_target,
            edge_type=primary_type,
            strength=primary_strength,
        )
        if len(items) == 1:
            return primary

        extras = items[1:]
        if all(edge_type == EdgeType.CORRELATES for _target, edge_type, _strength in extras):
            related = self._join_targets([target for target, _edge_type, _strength in extras])
            return f"{primary} It is also linked with {related}."

        details = [
            f"{target} ({self._relation_phrase(edge_type)})"
            for target, edge_type, _strength in extras
        ]
        if len(details) == 1:
            return f"{primary} It is also connected to {details[0]}."
        return f"{primary} It is also connected to {', '.join(details[:-1])}, and {details[-1]}."

    def train_from_records(
        self,
        records_path: Path,
        *,
        max_records: int = 50000,
        min_confidence: float = 0.3,
        min_samples: int = 20,
    ) -> dict:
        if not records_path.exists():
            return {"records_used": 0, "updated": False, "reason": "no_records_file"}

        lines = records_path.read_text(encoding="utf-8").splitlines()
        confidence_values: list[float] = []
        # phrase_scores: Dict[EdgeType, Dict[str, float]]
        phrase_scores: dict[EdgeType, dict[str, float]] = {}
        records_used = 0

        for line in reversed(lines):
            if records_used >= max_records:
                break
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue

            confidence = float(row.get("confidence", 0.0))
            if confidence < min_confidence:
                continue
            answer = str(row.get("answer", "")).lower()
            if not answer:
                continue

            confidence_values.append(confidence)

            # Analyze which phrases are associated with high-confidence answers
            for edge_type, phrases in self._relation_phrases.items():
                scores = phrase_scores.setdefault(edge_type, {})
                for phrase in phrases:
                    if phrase in answer:
                        scores[phrase] = scores.get(phrase, 0.0) + confidence

            records_used += 1

        if records_used < min_samples:
            return {"records_used": records_used, "updated": False, "reason": "not_enough_samples"}

        # Update preferred phrases based on score (cumulative confidence)
        for edge_type, scores in phrase_scores.items():
            if scores:
                best_phrase = max(scores, key=scores.get)
                # Ensure the best phrase is moved to the front
                phrases = self._relation_phrases[edge_type]
                if best_phrase in phrases:
                    phrases.remove(best_phrase)
                    phrases.insert(0, best_phrase)

        ordered_conf = sorted(confidence_values)
        idx_low = max(0, int(len(ordered_conf) * 0.2) - 1)
        idx_mid = max(0, int(len(ordered_conf) * 0.5) - 1)
        self.low_confidence_threshold = float(max(0.05, min(0.3, ordered_conf[idx_low])))
        self.medium_confidence_threshold = float(max(self.low_confidence_threshold + 0.02, min(0.6, ordered_conf[idx_mid])))

        if self.model_path is not None:
            self._save_model(self.model_path)

        return {
            "records_used": records_used,
            "updated": True,
            "low_confidence_threshold": self.low_confidence_threshold,
            "medium_confidence_threshold": self.medium_confidence_threshold,
            "median_confidence": float(median(confidence_values)) if confidence_values else 0.0,
            "model_path": str(self.model_path) if self.model_path is not None else "",
        }

    def _relation_phrase(self, edge_type: EdgeType) -> str:
        values = self._relation_phrases.get(edge_type)
        if not values:
            return "is related to"
        return values[0]

    def _single_relation_sentence(self, source: str, target: str, edge_type: EdgeType, strength: float) -> str:
        phrase = self._relation_phrase(edge_type)
        if strength < self.low_confidence_threshold:
            return f"Current memory weakly suggests that {source} {phrase} {target}."
        if strength < self.medium_confidence_threshold:
            return f"Current memory suggests that {source} {phrase} {target}."
        return f"{source.capitalize()} {phrase} {target}."

    @staticmethod
    def _join_targets(values: list[str]) -> str:
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return f"{', '.join(values[:-1])}, and {values[-1]}"

    def _load_model(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.low_confidence_threshold = float(payload.get("low_confidence_threshold", self.low_confidence_threshold))
        self.medium_confidence_threshold = float(payload.get("medium_confidence_threshold", self.medium_confidence_threshold))

    def _save_model(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "backend": self.backend,
            "low_confidence_threshold": self.low_confidence_threshold,
            "medium_confidence_threshold": self.medium_confidence_threshold,
        }
        path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
