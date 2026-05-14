"""
core/orchestrator.py — Cognitive Orchestration with full pipeline.

Pipeline:
  1. LLM parses intent + entities from raw text
  2. Graph builder encodes known facts into the graph
  3. Reasoner traverses graph for known facts
  4. If graph has facts → LLM refines them into fluent language
  5. If graph has NO facts → realtime Wikipedia lookup → LLM formats answer
  6. Background: ExpansionWorker learns the new facts into the graph for next time
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from core.logger import get_logger
from encoder.semantic_encoder import SemanticEncoder
from graph.graph_builder import GraphBuilder
from reasoning.router import ReasoningRouter
from decoder.response_formatter import ResponseFormatter
from decoder.language_generator import LanguageGenerator
from utils.realtime_lookup import fetch_realtime_answer

if TYPE_CHECKING:
    from .kernel import CognitiveKernel

log = get_logger(__name__)


class CognitiveOrchestrator:
    """
    Orchestrates the full cognitive pipeline.
    """

    def __init__(self, kernel: "CognitiveKernel") -> None:
        self.kernel = kernel
        self.encoder = SemanticEncoder(llm=self.kernel.llm)
        self.builder = GraphBuilder(self.kernel.graph)
        self.reasoning = ReasoningRouter(self.kernel.graph)
        self.formatter = ResponseFormatter()
        self.generator = LanguageGenerator(llm_refiner=self.kernel.llm)
        log.info(f"Orchestrator initialized. LLM backend: {self.kernel.llm.backend}")

    def process_query(self, text: str, user_id: str = "guest") -> Dict[str, Any]:
        """
        Full cognitive pipeline: Parse → Graph → Reason → Realtime → LLM → Format
        """
        log.info(f"Query: '{text}' (user={user_id})")

        # ── STEP 1: Parse intent with LLM (if available) ──────────────────────
        intent_kind = "unknown"
        llm_entities: List[str] = []
        requires_web = False

        if self.kernel.llm and self.kernel.llm.backend != "none":
            parsed = self.kernel.llm.parse_intent(text)
            intent_kind = parsed.kind
            llm_entities = parsed.entities or []
            requires_web = parsed.requires_web
            log.info(f"LLM intent: {intent_kind}, entities: {llm_entities}, web: {requires_web}")

        # Fast-path: greetings
        if intent_kind == "greeting":
            return self.formatter.format(
                text="Hello! Paragi Cognitive Runtime is online. How can I assist you today?",
                metadata={"mode": "greeting"}
            )

        # ── STEP 2: Encode + Build Graph ───────────────────────────────────────
        ir = self.encoder.encode(text)
        ir.intent = intent_kind
        if llm_entities:
            ir.entities = list(set(ir.entities + llm_entities))

        # Routing: personal vs world graph
        is_personal = intent_kind in ("personal_fact", "personal_query")
        target_graph = self.kernel.personal_graphs.get_graph(user_id) if is_personal else self.kernel.graph
        self.reasoning.set_graph(target_graph)
        self.builder.graph = target_graph
        self.builder.compile(ir)

        # Credit economy for contributed facts
        credits_awarded = 0
        if not is_personal and ir.relations:
            credits_awarded = 10 * len(ir.relations)
            self.kernel.user_state.award_credits(user_id, credits_awarded, "knowledge_contribution")

        # ── STEP 3: Reason over graph ──────────────────────────────────────────
        reasoning_result = self.reasoning.reason(ir)
        facts = reasoning_result.get("facts", [])
        chains = reasoning_result.get("chains", [])
        has_graph_knowledge = bool(facts or chains)
        log.info(f"Graph facts found: {len(facts)}, chains: {len(chains)}")

        # ── STEP 4A: Graph has knowledge → LLM refines it ─────────────────────
        if has_graph_knowledge:
            answer = self.generator.generate(reasoning_result, original_query=text)

        # ── STEP 4B: No graph knowledge → check if Wikipedia is appropriate ───
        else:
            # Only search Wikipedia for factual lookups (who/what is X, define X, etc.)
            # NOT for conversational/simple factual questions ("is water cold?")
            should_search_web = requires_web or intent_kind in ("concept", "relation", "general_fact")
            web_result = fetch_realtime_answer(text) if should_search_web else None

            if web_result:
                raw_summary, source = web_result
                log.info(f"Realtime answer from: {source}")

                # Use LLM to format the web result into a clean, natural response
                if self.kernel.llm and self.kernel.llm.backend != "none":
                    refine = self.kernel.llm.format_response(
                        question=text,
                        graph_answer=raw_summary,
                        node_path=[],
                        confidence=0.6,
                        intent_kind=intent_kind
                    )
                    answer = refine.answer
                else:
                    answer = raw_summary

                # Background: enqueue concepts for graph expansion
                all_concepts = list(set(ir.concepts + ir.entities))
                for concept in all_concepts:
                    self.kernel.expansion.enqueue(concept)

                # Digest web knowledge directly into graph edges
                if self.kernel.llm and self.kernel.llm.backend != "none":
                    edges = self.kernel.llm.digest_into_graph(raw_summary)
                    for edge in edges:
                        from core.enums import EdgeType
                        self.builder.create_or_reinforce_edge(
                            source_label=edge["source"],
                            target_label=edge["target"],
                            edge_type=EdgeType.get(edge["relation"], EdgeType.ASSOCIATED_WITH),
                        )
                    if edges:
                        log.info(f"Digested {len(edges)} edges from web result into graph")

            else:
                # Pure LLM answer — no graph, no web (handles "is water cold?" etc.)
                log.info("No realtime result. Using pure LLM fallback.")
                if self.kernel.llm and self.kernel.llm.backend != "none":
                    refine = self.kernel.llm.format_response(
                        question=text,
                        graph_answer="",
                        node_path=[],
                        confidence=0.0,
                        intent_kind=intent_kind
                    )
                    answer = refine.answer
                else:
                    answer = "I don't have information on that topic yet. Try teaching me by stating facts directly."

        # ── STEP 5: Format final response ──────────────────────────────────────
        response = self.formatter.format(
            text=answer,
            metadata=reasoning_result
        )
        response["credits_awarded"] = credits_awarded
        response["scope"] = "personal" if is_personal else "main"
        response["user_id"] = user_id
        return response
