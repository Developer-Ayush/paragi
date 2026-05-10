"""
reasoning/router.py — Reasoning Dispatcher.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from core.semantic_ir import SemanticIR
from core.enums import ReasoningMode
from graph.graph import CognitiveGraph

from .causal_reasoner import CausalReasoner
from .analogy_reasoner import AnalogyReasoner
from .temporal_reasoner import TemporalReasoner
from .contradiction_reasoner import ContradictionReasoner
from .abstraction_reasoner import AbstractionReasoner


class ReasoningRouter:
    """
    Orchestrates the selection and execution of specialized reasoners.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self.graph = graph
        self._reasoners = {
            ReasoningMode.CAUSAL: CausalReasoner(graph),
            ReasoningMode.ANALOGY: AnalogyReasoner(graph),
            ReasoningMode.TEMPORAL: TemporalReasoner(graph),
            ReasoningMode.CONTRADICTION: ContradictionReasoner(graph),
            ReasoningMode.ABSTRACTION: AbstractionReasoner(graph),
        }

    def set_graph(self, graph: CognitiveGraph) -> None:
        """Update the graph for all internal reasoners."""
        self.graph = graph
        for reasoner in self._reasoners.values():
            reasoner.graph = graph

    def reason(self, ir: SemanticIR) -> Dict[str, Any]:
        """
        Dispatches to the appropriate reasoner based on IR mode.
        """
        mode_val = ir.metadata.get("reasoning_mode", "general")
        try:
            mode = ReasoningMode(mode_val)
        except ValueError:
            mode = ReasoningMode.GENERAL
            
        reasoner = self._reasoners.get(mode)
        
        if not reasoner:
            # Fallback
            reasoner = self._reasoners[ReasoningMode.CAUSAL]
            
        return reasoner.reason(ir)