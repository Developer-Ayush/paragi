"""reasoning/engine.py — ReasoningEngine: orchestrates a full reasoning pass."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.semantic_ir import SemanticIR
from core.enums import ReasoningMode
from core.constants import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, EDGE_RELATION_TEXT
from core.logger import get_logger
from graph.graph import GraphEngine, PathMatch
from .router import ReasoningRouter, RoutingDecision
from .scorer import score_paths, summarize_paths
from .confidence import compute_path_confidence, consensus_confidence

log = get_logger(__name__)


@dataclass
class ReasoningResult:
    """Output of a full reasoning pass."""
    answer: str
    confidence: float
    paths: List[PathMatch] = field(default_factory=list)
    node_path: List[str] = field(default_factory=list)
    mode: str = "general"
    scope: str = "main"
    domain: str = "general"
    used_fallback: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


class ReasoningEngine:
    """
    Orchestrates the full reasoning pass:
      SemanticIR → ReasoningRouter → Reasoner(s) → ReasoningResult

    All reasoning is graph-algorithmic. No LLM token generation happens here.
    """

    def __init__(self, graph: GraphEngine) -> None:
        self.graph = graph
        self.router = ReasoningRouter()

    def reason(self, ir: SemanticIR) -> ReasoningResult:
        """Run the full reasoning pipeline for this SemanticIR."""
        routing = self.router.route(ir)
        log.debug(f"Routing: {routing.primary_mode.value} ({routing.reasoning})")

        # ── Personal memory shortcut ───────────────────────────────────────
        if ir.intent == "personal_query" and ir.personal_attribute:
            return self._personal_query(ir)

        if ir.intent == "personal_fact":
            res = ReasoningResult(
                answer=f"Got it. I'll remember your {ir.personal_attribute}.",
                confidence=0.99, mode="personal", scope="personal",
            )
            print(f"DEBUG_REASONING: intent=personal_fact scope={res.scope}")
            return res

        if ir.intent == "greeting":
            return ReasoningResult(
                answer="Hello! How can I help you today?",
                confidence=1.0, mode="greeting",
            )

        # ── Route to primary reasoner ──────────────────────────────────────
        result = self._dispatch(ir, routing)

        # ── Try secondary if primary yields nothing ────────────────────────
        if result.confidence < 0.1 and routing.secondary_modes:
            for secondary in routing.secondary_modes:
                secondary_routing = RoutingDecision(primary_mode=secondary, confidence=0.6)
                alt = self._dispatch(ir, secondary_routing)
                if alt.confidence > result.confidence:
                    result = alt
                    break

        return result

    def _dispatch(self, ir: SemanticIR, routing: RoutingDecision) -> ReasoningResult:
        mode = routing.primary_mode
        src = ir.source_concept
        tgt = ir.target_concept or ir.target_concept
        concept = ir.source_concept or ir.target_concept or (ir.entities[0] if ir.entities else None)

        if mode == ReasoningMode.CAUSAL and src and tgt:
            return self._causal(ir, src, tgt)
        elif mode == ReasoningMode.TEMPORAL and src and tgt:
            return self._temporal(ir, src, tgt)
        elif mode == ReasoningMode.ANALOGY and concept:
            return self._analogy(ir, concept)
        elif mode == ReasoningMode.ABSTRACTION and concept:
            return self._abstraction(ir, concept)
        elif mode == ReasoningMode.PREDICTIVE and src:
            return self._predictive(ir, src)
        elif mode == ReasoningMode.CONTRADICTION and src and tgt:
            return self._contradiction(ir, src, tgt)
        elif ir.requires_web:
            return self._realtime(ir)
        else:
            return self._general(ir, concept)

    # ── Reasoner implementations ───────────────────────────────────────────

    def _causal(self, ir: SemanticIR, source: str, target: str) -> ReasoningResult:
        from .causal_reasoner import causal_reason
        return causal_reason(self.graph, ir, source, target)

    def _temporal(self, ir: SemanticIR, source: str, target: str) -> ReasoningResult:
        from .temporal_reasoner import temporal_reason
        return temporal_reason(self.graph, ir, source, target)

    def _analogy(self, ir: SemanticIR, concept: str) -> ReasoningResult:
        from .analogy_reasoner import analogy_reason
        return analogy_reason(self.graph, ir, concept)

    def _abstraction(self, ir: SemanticIR, concept: str) -> ReasoningResult:
        from .abstraction_reasoner import abstraction_reason
        return abstraction_reason(self.graph, ir, concept)

    def _predictive(self, ir: SemanticIR, source: str) -> ReasoningResult:
        from .predictive_reasoner import predictive_reason
        return predictive_reason(self.graph, ir, source)

    def _contradiction(self, ir: SemanticIR, source: str, target: str) -> ReasoningResult:
        from .contradiction_reasoner import contradiction_reason
        return contradiction_reason(self.graph, ir, source, target)

    def _general(self, ir: SemanticIR, concept: Optional[str]) -> ReasoningResult:
        if not concept:
            return ReasoningResult(answer="", confidence=0.0, used_fallback=True)

        # Concept lookup: find strongest outgoing edges
        neighbors = self.graph.get_neighbors(concept)
        if not neighbors:
            return ReasoningResult(answer="", confidence=0.0, used_fallback=True)

        neighbors.sort(key=lambda e: -e.strength)
        top = neighbors[:5]
        parts = []
        for edge in top:
            tgt_label = self.graph.get_node_label(edge.target)
            rel_text = EDGE_RELATION_TEXT.get(edge.type, "is related to")
            parts.append(f"{concept} {rel_text} {tgt_label}")
        answer = ". ".join(parts) + "."
        confidence = compute_path_confidence([]) + top[0].strength * 0.5 if top else 0.1
        node_path = [concept] + [self.graph.get_node_label(e.target) for e in top[:3]]
        return ReasoningResult(
            answer=answer, confidence=min(0.85, confidence),
            node_path=node_path, mode="general",
        )

    def _realtime(self, ir: SemanticIR) -> ReasoningResult:
        return ReasoningResult(
            answer="Looking that up in real-time...",
            confidence=0.5, mode="realtime",
        )

    def _personal_query(self, ir: SemanticIR) -> ReasoningResult:
        attr = ir.personal_attribute or ""
        neighbors = self.graph.get_neighbors("self")
        for edge in neighbors:
            target_label = self.graph.get_node_label(edge.target)
            if attr and attr in target_label:
                value = target_label.replace(attr, "").strip()
                return ReasoningResult(
                    answer=value or target_label,
                    confidence=0.9, mode="personal", scope="personal",
                )
        return ReasoningResult(answer="", confidence=0.0, used_fallback=True, scope="personal")
