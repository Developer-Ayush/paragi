"""reasoning/router.py — ReasoningRouter: maps SemanticIR to reasoning strategies.

Replaces the 14-line stub with a full routing engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from core.semantic_ir import SemanticIR
from core.enums import ReasoningMode
from core.constants import (
    CAUSAL_KEYWORDS, TEMPORAL_KEYWORDS, ANALOGY_KEYWORDS,
    PLANNING_KEYWORDS, PREDICTION_KEYWORDS, CONTRADICTION_KEYWORDS,
)


@dataclass
class RoutingDecision:
    """Result of the reasoning router: which reasoners to invoke and in what order."""
    primary_mode: ReasoningMode
    secondary_modes: List[ReasoningMode] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""


class ReasoningRouter:
    """
    Routes a SemanticIR to the appropriate reasoning strategy.

    Priority (highest first):
      1. IR.reasoning_mode (set by encoder)
      2. IR.intent + query_type
      3. Keyword scan of normalized text
      4. Default: GENERAL
    """

    def route(self, ir: SemanticIR) -> RoutingDecision:
        """Determine the primary + secondary reasoning modes for this IR."""

        # ── Priority 1: explicit mode from encoder ─────────────────────────
        mode_from_ir = self._from_string(ir.reasoning_mode)
        if mode_from_ir is not None and mode_from_ir != ReasoningMode.GENERAL:
            secondaries = self._keyword_modes(ir.normalized_text, exclude=mode_from_ir)
            return RoutingDecision(
                primary_mode=mode_from_ir,
                secondary_modes=secondaries,
                confidence=0.9,
                reasoning="encoder_mode",
            )

        # ── Priority 2: query_type from intent classifier ──────────────────
        mode_from_qt = self._from_query_type(ir.query_type)
        if mode_from_qt is not None:
            secondaries = self._keyword_modes(ir.normalized_text, exclude=mode_from_qt)
            return RoutingDecision(
                primary_mode=mode_from_qt,
                secondary_modes=secondaries,
                confidence=0.8,
                reasoning="query_type",
            )

        # ── Priority 3: keyword scan ───────────────────────────────────────
        keyword_modes = self._keyword_modes(ir.normalized_text)
        if keyword_modes:
            primary = keyword_modes[0]
            return RoutingDecision(
                primary_mode=primary,
                secondary_modes=keyword_modes[1:],
                confidence=0.7,
                reasoning="keyword_scan",
            )

        # ── Default ────────────────────────────────────────────────────────
        return RoutingDecision(
            primary_mode=ReasoningMode.GENERAL,
            confidence=0.5,
            reasoning="default",
        )

    @staticmethod
    def _from_string(s: str) -> ReasoningMode | None:
        mapping = {
            "causal": ReasoningMode.CAUSAL,
            "temporal": ReasoningMode.TEMPORAL,
            "analogy": ReasoningMode.ANALOGY,
            "analogy_question": ReasoningMode.ANALOGY,
            "abstraction": ReasoningMode.ABSTRACTION,
            "predictive": ReasoningMode.PREDICTIVE,
            "contradiction": ReasoningMode.CONTRADICTION,
            "planning": ReasoningMode.PLANNING,
            "probabilistic": ReasoningMode.PROBABILISTIC,
            "general": ReasoningMode.GENERAL,
        }
        return mapping.get((s or "").strip().lower())

    @staticmethod
    def _from_query_type(qt: str) -> ReasoningMode | None:
        mapping = {
            "CAUSAL_REASONING":       ReasoningMode.CAUSAL,
            "TEMPORAL_REASONING":     ReasoningMode.TEMPORAL,
            "ANALOGICAL_REASONING":   ReasoningMode.ANALOGY,
            "EXPLORATORY_REASONING":  ReasoningMode.ABSTRACTION,
            "PLANNING":               ReasoningMode.PLANNING,
            "CONTRADICTION":          ReasoningMode.CONTRADICTION,
        }
        return mapping.get((qt or "").strip().upper())

    @staticmethod
    def _keyword_modes(text: str, exclude: ReasoningMode | None = None) -> List[ReasoningMode]:
        token_set = set(text.lower().split())
        modes: List[ReasoningMode] = []
        checks = [
            (CAUSAL_KEYWORDS,        ReasoningMode.CAUSAL),
            (TEMPORAL_KEYWORDS,      ReasoningMode.TEMPORAL),
            (ANALOGY_KEYWORDS,       ReasoningMode.ANALOGY),
            (PLANNING_KEYWORDS,      ReasoningMode.PLANNING),
            (PREDICTION_KEYWORDS,    ReasoningMode.PREDICTIVE),
            (CONTRADICTION_KEYWORDS, ReasoningMode.CONTRADICTION),
        ]
        for keywords, mode in checks:
            if mode != exclude and token_set & keywords:
                modes.append(mode)
        return modes


# Module-level convenience
_default_router = ReasoningRouter()


def detect_reasoning_mode(text: str) -> str:
    """Backward-compatible function (replaces the 14-line stub)."""
    from core.semantic_ir import SemanticIR
    dummy_ir = SemanticIR(
        intent="unknown", reasoning_mode="general",
        normalized_text=text, raw_text=text,
    )
    decision = _default_router.route(dummy_ir)
    return decision.primary_mode.value