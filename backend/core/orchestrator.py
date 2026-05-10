"""
core/orchestrator.py — Cognitive Orchestration with OS-level routing.
"""
from __future__ import annotations

import time
from typing import Dict, Any, TYPE_CHECKING
from core.logger import get_logger
from encoder.semantic_encoder import SemanticEncoder
from graph.graph_builder import GraphBuilder
from reasoning.router import ReasoningRouter
from decoder.response_formatter import ResponseFormatter
from decoder.language_generator import LanguageGenerator

if TYPE_CHECKING:
    from .kernel import CognitiveKernel

log = get_logger(__name__)


class CognitiveOrchestrator:
    """
    Orchestrates the cognitive pipeline: Compile, Reason, Reconstruct, Generate, Format.
    """

    def __init__(self, kernel: CognitiveKernel) -> None:
        self.kernel = kernel
        self.encoder = SemanticEncoder()
        self.builder = GraphBuilder(self.kernel.graph)
        self.reasoning = ReasoningRouter(self.kernel.graph)
        self.formatter = ResponseFormatter()
        self.generator = LanguageGenerator(llm_refiner=self.kernel.llm)
        log.info(f"Orchestrator initialized with LLM backend: {self.kernel.llm.backend}")

    def process_query(self, text: str, user_id: str = "guest") -> Dict[str, Any]:
        """
        Executes the full cognitive pipeline with OS-level routing and economy.
        """
        log.info(f"Processing query: {text} (user: {user_id})")
        
        # 1. Encode: Human Language -> SemanticIR
        ir = self.encoder.encode(text)
        
        # ── OS Layer: Intent-Based Routing ────────────────────────────────────
        # Determine if this is a personal fact or a world-knowledge query
        is_personal = ir.intent in ("personal_fact", "personal_query")
        target_graph = self.kernel.personal_graphs.get_graph(user_id) if is_personal else self.kernel.graph
        
        # Update reasoning router and builder with target graph for this query
        self.reasoning.set_graph(target_graph)
        self.builder.graph = target_graph
        
        # ── OS Layer: Bloom Filter Fast Check ─────────────────────────────────
        # (Optimization: Skip expansion worker if concept definitely exists)
        
        # 2. Build/Reinforce: Update target graph with query context
        self.builder.compile(ir)
        
        # ── OS Layer: Cognitive Economy ───────────────────────────────────────
        credits_awarded = 0
        if not is_personal and len(ir.relations) > 0:
            # Award credits for world-knowledge contributions
            credits_awarded = 10 * len(ir.relations)
            self.kernel.user_state.award_credits(user_id, credits_awarded, "knowledge_contribution")

        # 3. Reason: SemanticIR -> ReasoningResult
        reasoning_result = self.reasoning.reason(ir)
        
        # 4. Decode & Format: ReasoningResult -> Final API Output
        # Extract primary answer from reasoner result
        chains = reasoning_result.get("chains", [])
        
        # Determine base answer
        if ir.intent == "greeting":
            answer = "Hello. Paragi Cognitive Runtime is online. How can I assist with your knowledge graph today?"
        elif chains:
            # Generate actual language from graph chains
            answer = self.generator.generate(reasoning_result, original_query=text)
        else:
            # Trigger autonomous expansion for unknown concepts (§4.2)
            all_concepts = list(set(ir.concepts + ir.entities))
            if all_concepts:
                for concept in all_concepts:
                    self.kernel.expansion.enqueue(concept)
                answer = "I don't have enough information to form a reasoning chain right now. I've initiated an autonomous knowledge expansion for these concepts. Ask me again in a few moments."
            else:
                answer = "I don't have enough information to form a reasoning chain."
            
        response = self.formatter.format(
            text=answer,
            metadata=reasoning_result
        )
        
        # Add OS metadata
        response["credits_awarded"] = credits_awarded
        response["scope"] = "personal" if is_personal else "main"
        response["user_id"] = user_id
        
        return response
