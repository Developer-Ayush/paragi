"""cognition/consciousness.py — Top-level cognitive orchestrator.

This is the main cognition loop: takes a SemanticIR and produces a
ReasoningResult by coordinating graph building, reasoning, and memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.semantic_ir import SemanticIR
from core.logger import get_logger
from graph.graph import GraphEngine
from graph.graph_builder import GraphBuilder
from graph.memory.working import WorkingMemory
from graph.memory.episodic import EpisodicMemory
from reasoning.engine import ReasoningEngine, ReasoningResult

log = get_logger(__name__)


class CognitionEngine:
    """
    The top-level cognition orchestrator.

    Pipeline:
        SemanticIR
          → GraphBuilder (update graph)
          → WorkingMemory (store context)
          → ReasoningEngine (graph traversal)
          → ReasoningResult
    """

    def __init__(
        self,
        graph: GraphEngine,
        *,
        working_memory: Optional[WorkingMemory] = None,
        episodic_memory: Optional[EpisodicMemory] = None,
        learning_confidence_threshold: float = 0.5,
    ) -> None:
        self.graph = graph
        self.working_memory = working_memory or WorkingMemory()
        self.episodic_memory = episodic_memory or EpisodicMemory()
        self.graph_builder = GraphBuilder(graph)
        self.reasoning_engine = ReasoningEngine(graph)
        self.learning_confidence_threshold = learning_confidence_threshold

    def process(self, ir: SemanticIR) -> ReasoningResult:
        """Run the full cognitive pipeline for a SemanticIR."""

        # ── 1. Store context in working memory ─────────────────────────────
        if ir.raw_text:
            self.working_memory.set(f"query_{ir.intent}", ir.raw_text)

        # ── 2. Graph builder: learn from IR (if learnability qualifies) ────
        allow_learning = (
            ir.learnability >= self.learning_confidence_threshold
            and not ir.requires_web
            and ir.temporal_data.temporal_nature != "realtime"
        )
        nodes_added, edges_added = self.graph_builder.insert(ir, allow_learning=allow_learning)
        if nodes_added > 0 or edges_added > 0:
            log.debug(f"Graph updated: +{nodes_added} nodes, +{edges_added} edges")

        # ── 3. Store personal facts in episodic memory ─────────────────────
        if ir.intent == "personal_fact" and ir.personal_attribute and ir.personal_value:
            self.episodic_memory.store(
                key=f"personal_{ir.personal_attribute}",
                value=ir.personal_value,
                source="user",
            )

        # ── 4. Augment activation targets with working memory context ──────
        wm_context = self.working_memory.get_all()

        # ── 5. Run reasoning ───────────────────────────────────────────────
        result = self.reasoning_engine.reason(ir)

        # ── 6. Strengthen traversed edges ─────────────────────────────────
        if result.paths:
            for path in result.paths[:3]:
                for edge_id in path.edge_ids:
                    self.graph.strengthen_edge(edge_id)

        log.debug(
            f"Cognition complete: intent={ir.intent} mode={result.mode} "
            f"confidence={result.confidence:.2f} answer_len={len(result.answer)}"
        )
        return result
