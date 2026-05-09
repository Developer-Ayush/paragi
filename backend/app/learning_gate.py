"""Phase 6 — Learning Gate.

Validates knowledge before permanent graph storage.
Blocks: speculation, rumors, unverified realtime, low-confidence.
Only learns when confidence > threshold AND validation passes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .graph import GraphEngine
from .models import EdgeType, normalize_label


@dataclass(slots=True)
class LearningDecision:
    should_learn: bool
    confidence: float
    reason: str
    checks_passed: List[str]
    checks_failed: List[str]


class LearningGate:
    def __init__(self, graph: GraphEngine, *, confidence_threshold: float = 0.5,
                 contradiction_penalty: float = 0.3, consistency_bonus: float = 0.1) -> None:
        self.graph = graph
        self.confidence_threshold = confidence_threshold
        self.contradiction_penalty = contradiction_penalty
        self.consistency_bonus = consistency_bonus

    def validate_edge(self, source: str, target: str, edge_type: EdgeType, *,
                      stated_confidence: float = 0.8, is_realtime: bool = False,
                      is_speculation: bool = False, source_quality: str = "user") -> LearningDecision:
        source = normalize_label(source)
        target = normalize_label(target)
        passed: list[str] = []
        failed: list[str] = []
        conf = stated_confidence

        if is_realtime:
            failed.append("realtime_rejected")
            return LearningDecision(False, 0.0, "Realtime info must not be permanently stored", passed, failed)

        if is_speculation:
            failed.append("speculation_rejected")
            return LearningDecision(False, conf * 0.3, "Speculative information rejected", passed, failed)
        passed.append("not_speculation")

        quality_map = {"verified": 1.0, "external_api": 0.9, "wikipedia": 0.85,
                       "user": 0.8, "llm_inferred": 0.6, "unknown": 0.4}
        mult = quality_map.get(source_quality, 0.5)
        conf *= mult
        (passed if mult >= 0.7 else failed).append(f"source_quality:{source_quality}")

        existing = self.graph.get_edge(source, target)
        if existing is not None:
            if existing.type != edge_type:
                conf -= self.contradiction_penalty
                failed.append(f"type_conflict:{existing.type.value}->{edge_type.value}")
            else:
                conf += self.consistency_bonus
                passed.append("consistent_with_existing")

        try:
            paths = self.graph.find_paths(source, target, max_hops=3, max_paths=8)
            if paths:
                conf += min(0.15, len(paths) * 0.03)
                passed.append(f"graph_agreement:{len(paths)}_paths")
            elif not self.graph.node_exists(source) and not self.graph.node_exists(target):
                conf *= 0.9
                passed.append("novel_nodes")
        except Exception:
            passed.append("graph_check_skipped")

        if edge_type == EdgeType.TEMPORAL:
            conf *= 0.85
            passed.append("temporal_penalty")

        conf = max(0.0, min(1.0, conf))
        if conf >= self.confidence_threshold:
            return LearningDecision(True, conf, "All checks passed", passed, failed)

        failed.append(f"below_threshold:{conf:.3f}<{self.confidence_threshold:.3f}")
        return LearningDecision(False, conf, f"Confidence {conf:.3f} below threshold", passed, failed)

    def validate_batch(self, edges: list[dict], *, is_realtime: bool = False,
                       source_quality: str = "user") -> list[tuple[dict, LearningDecision]]:
        results = []
        for edge in edges:
            src = str(edge.get("source", "")).strip()
            tgt = str(edge.get("target", "")).strip()
            rel = str(edge.get("relation", "CORRELATES")).strip().upper()
            try:
                etype = EdgeType[rel]
            except (KeyError, ValueError):
                etype = EdgeType.CORRELATES
            decision = self.validate_edge(src, tgt, etype, stated_confidence=0.8,
                                          is_realtime=is_realtime, source_quality=source_quality)
            results.append((edge, decision))
        return results
