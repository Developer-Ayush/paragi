from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from .expansion import ExpansionQueueStore, ExpansionResolver
from .graph import GraphEngine, PathMatch
from .models import EdgeType, normalize_label
from .query_control import ActivationProfile, QueryClassifier
from .llm_refiner import LLMRefiner, RefineResult


@dataclass(slots=True)
class EncodedQuery:
    raw_text: str
    tokens: list[str]
    semantic_vector: list[float]  # 700 dims
    backend: str


@dataclass(slots=True)
class QueryIntent:
    kind: str
    source: str | None = None
    target: str | None = None
    concept: str | None = None
    personal_attribute: str | None = None
    personal_value: str | None = None


@dataclass(slots=True)
class QueryResponse:
    answer: str
    raw_text: str
    source: str | None
    target: str | None
    used_fallback: bool
    created_edges: int
    confidence: float
    node_path: list[str]
    steps: list[str]
    encoder_backend: str
    activation_ranges: list[tuple[int, int]]
    active_dims: int
    shortcut_applied: bool
    expansion_node_id: str | None
    new_nodes_created: int


class TemporaryEncoder:
    token_re = re.compile(r"[a-z0-9_]+")

    def __init__(self, *, use_fastembed: bool = False) -> None:
        self._backend = "hash"
        self._embedder = None
        if use_fastembed:
            try:
                from fastembed import TextEmbedding  # type: ignore

                self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
                self._backend = "fastembed"
            except Exception:
                self._embedder = None
                self._backend = "hash"

    def encode(self, text: str) -> EncodedQuery:
        normalized = normalize_label(text)
        tokens = self.token_re.findall(normalized)
        vector_384 = self._embed_384(normalized, tokens)
        vector_700 = [0.0] * 700
        # Phase-3 bridge: 384 temporary semantic dims mapped into 250..579 range.
        # This range avoids overlaps with:
        # §3.2 Emotional/Psychological (175-249)
        # §3.2 Factual (580-639)
        # We use as many of the 384 dims as fit into 250-579 (which is 330 dims).
        for idx, value in enumerate(vector_384):
            target_idx = 250 + idx
            if target_idx <= 579:
                vector_700[target_idx] = float(value)
        return EncodedQuery(
            raw_text=normalized,
            tokens=tokens,
            semantic_vector=vector_700,
            backend=self._backend,
        )

    def _embed_384(self, text: str, tokens: list[str]) -> list[float]:
        if self._embedder is not None:
            try:
                values = next(iter(self._embedder.embed([text])))
                return self._normalize(list(values))
            except Exception:
                pass
        return self._hash_embed(tokens or [text])

    def _hash_embed(self, tokens: Sequence[str]) -> list[float]:
        dims = 384
        vec = [0.0] * dims
        for token in tokens:
            digest = hashlib.blake2s(token.encode("utf-8"), digest_size=16).digest()
            for slot in range(6):
                index = int.from_bytes(digest[slot * 2 : slot * 2 + 2], "big") % dims
                sign = 1.0 if digest[12 + (slot % 4)] % 2 == 0 else -1.0
                vec[index] += sign
        return self._normalize(vec)

    @staticmethod
    def _normalize(values: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in values))
        if norm <= 1e-12:
            return values
        return [v / norm for v in values]


class TemporaryDecoder:
    backend = "temporary"

    _relation_verb = {
        EdgeType.CAUSES: "can cause",
        EdgeType.CORRELATES: "is associated with",
        EdgeType.IS_A: "is a type of",
        EdgeType.TEMPORAL: "usually happens before",
        EdgeType.INFERRED: "is likely related to",
    }

    def decode_path(self, path: PathMatch) -> str:
        if path.hops == 0 or len(path.node_labels) < 2:
            return "I do not have enough reliable memory yet to answer this."
        if path.hops == 1:
            source = path.node_labels[0]
            target = path.node_labels[1]
            edge_type = path.edge_types[0]
            strength = path.edge_strengths[0] if path.edge_strengths else 0.0
            return self._single_relation_sentence(source, target, edge_type, strength)

        clauses: list[str] = []
        for idx, edge_type in enumerate(path.edge_types):
            source = path.node_labels[idx]
            target = path.node_labels[idx + 1]
            verb = self._relation_verb.get(edge_type, "is related to")
            clauses.append(f"{source} {verb} {target}")

        if len(clauses) == 2:
            return f"{clauses[0].capitalize()}, and {clauses[1]}."

        trail = ", then ".join(clauses[1:])
        first = clauses[0].capitalize()
        return f"{first}; then {trail}. So {path.node_labels[0]} is linked to {path.node_labels[-1]}."

    def decode_concept(self, concept: str, neighbors: Iterable[tuple[str, EdgeType, float]]) -> str:
        items = list(neighbors)
        if not items:
            return f"I do not have enough reliable information about {concept} yet."

        primary_target, primary_type, primary_strength = items[0]
        primary = self._single_relation_sentence(concept, primary_target, primary_type, primary_strength)

        if len(items) == 1:
            return primary

        extras = items[1:]
        if all(edge_type == EdgeType.CORRELATES for _target, edge_type, _strength in extras):
            related = self._join_targets([target for target, _edge_type, _strength in extras])
            return f"{primary} It is also linked with {related}."

        others: list[str] = []
        for target, edge_type, _strength in extras:
            verb = self._relation_verb.get(edge_type, "is related to")
            others.append(f"{target} ({verb})")
        if len(others) == 1:
            return f"{primary} It is also connected to {others[0]}."
        return f"{primary} It is also connected to {', '.join(others[:-1])}, and {others[-1]}."

    def _single_relation_sentence(self, source: str, target: str, edge_type: EdgeType, strength: float) -> str:
        verb = self._relation_verb.get(edge_type, "is related to")
        base = f"{source.capitalize()} {verb} {target}."
        if strength < 0.12:
            return f"Current memory weakly suggests that {source} {verb} {target}."
        if strength < 0.25:
            return f"Current memory suggests that {source} {verb} {target}."
        return base

    @staticmethod
    def _join_targets(values: list[str]) -> str:
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return f"{', '.join(values[:-1])}, and {values[-1]}"


class QueryPipeline:
    relation_patterns = [
        re.compile(r"^\s*(?:does|can|could|will)\s+([a-z0-9_]+)\s+([a-z0-9_]+)\??\s*$"),
        re.compile(r"^\s*is\s+([a-z0-9_]+)\s+([a-z0-9_]+)\??\s*$"),
    ]
    concept_patterns = [
        re.compile(r"^\s*what\s+(?:is+|are)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*who\s+(?:is+|was|are)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*(?:define|describe|explain)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*tell\s+me\s+about\s+(.+?)\??\s*$"),
        re.compile(r"^\s*how\s+(?:much|many|big|old|tall|fast|far|long)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*how\s+(?:do|does|did|is|are|was|were|can|could)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*where\s+(?:is|are|was|were|do|does|did|can)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*when\s+(?:is|are|was|were|do|does|did|will)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*why\s+(?:is|are|do|does|did|was|were|can)\s+(.+?)\??\s*$"),
        re.compile(r"^\s*(.+?\s+of\s+.+?)\??\s*$"),
    ]
    general_fact_pattern = re.compile(r"^\s*(.+?)\s+is\s+(.+?)\s*$")
    personal_patterns = [
        (re.compile(r"^\s*my\s+name\s+is\s+([a-z0-9_ ]+)\s*$"), "name"),
        (re.compile(r"^\s*my\s+nationality\s+is\s+([a-z0-9_ ]+)\s*$"), "nationality"),
        (re.compile(r"^\s*i\s+am\s+from\s+([a-z0-9_ ]+)\s*$"), "nationality"),
        (re.compile(r"^\s*i\s+am\s+([a-z0-9_ ]+)\s*$"), "identity"),
        (re.compile(r"^\s*i\s+live\s+in\s+([a-z0-9_ ]+)\s*$"), "location"),
        (re.compile(r"^\s*i\s+like\s+([a-z0-9_ ]+)\s*$"), "preference"),
    ]
    personal_fact_generic_pattern = re.compile(r"^\s*my\s+([a-z0-9_ ]{1,80}?)\s+is\s+([a-z0-9_ ]+)\s*$")
    personal_query_patterns = [
        (re.compile(r"^\s*what\s+is\s+my\s+name\??\s*$"), "name"),
        (re.compile(r"^\s*what\s+is\s+my\s+nationality\??\s*$"), "nationality"),
        (re.compile(r"^\s*where\s+am\s+i\s+from\??\s*$"), "nationality"),
        (re.compile(r"^\s*who\s+am\s+i\??\s*$"), "identity"),
        (re.compile(r"^\s*what\s+is\s+my\s+identity\??\s*$"), "identity"),
        (re.compile(r"^\s*where\s+do\s+i\s+live\??\s*$"), "location"),
        (re.compile(r"^\s*where\s+do\s+i\s+work\??\s*$"), "work"),
        (re.compile(r"^\s*what\s+do\s+i\s+like\??\s*$"), "preference"),
        (re.compile(r"^\s*what\s+is\s+my\s+email\??\s*$"), "email"),
        (re.compile(r"^\s*what\s+is\s+my\s+phone\??\s*$"), "phone"),
        (re.compile(r"^\s*what\s+is\s+my\s+address\??\s*$"), "address"),
    ]
    personal_query_generic_pattern = re.compile(r"^\s*what\s+is\s+my\s+([a-z0-9_ ]+)\??\s*$")

    def __init__(
        self,
        graph: GraphEngine,
        encoder: TemporaryEncoder,
        decoder: TemporaryDecoder,
        *,
        classifier: QueryClassifier | None = None,
        expansion_queue: ExpansionQueueStore | None = None,
        expansion_resolver: ExpansionResolver | None = None,
        llm: LLMRefiner | None = None,
    ) -> None:
        self.graph = graph
        self.encoder = encoder
        self.decoder = decoder
        self.classifier = classifier or QueryClassifier()
        self.expansion_queue = expansion_queue
        self.expansion_resolver = expansion_resolver
        self.llm = llm
        self._query_counts: dict[str, int] = {}

    def run(self, text: str, *, max_hops: int = 7, max_paths: int = 64, allow_learning: bool = True) -> QueryResponse:
        encoded = self.encoder.encode(text)
        recall_count = self._query_counts.get(encoded.raw_text, 0)
        profile = self.classifier.classify(encoded.raw_text, encoded.tokens, recall_count)
        self._query_counts[encoded.raw_text] = recall_count + 1

        llm_intent = None
        if self.llm:
            llm_intent = self.llm.parse_intent(text)
            if llm_intent.kind != "unknown" and not llm_intent.error:
                intent = QueryIntent(
                    kind=llm_intent.kind,
                    source=llm_intent.source,
                    target=llm_intent.target,
                    concept=llm_intent.concept,
                    personal_attribute=llm_intent.personal_attribute,
                    personal_value=llm_intent.personal_value,
                )
                steps.append(f"llm_intent:{intent.kind}")
            else:
                intent = self._parse_intent(encoded.raw_text)
                steps.append(f"regex_intent:{intent.kind}")
        else:
            intent = self._parse_intent(encoded.raw_text)
            steps.append(f"regex_intent:{intent.kind}")

        # Learning Step: If LLM extracted edges, apply them
        created_edges = 0
        new_nodes = 0
        if allow_learning and llm_intent and llm_intent.graph_edges:
            c, n = self._apply_llm_edges(llm_intent.graph_edges, encoded, profile)
            created_edges += c
            new_nodes += n
            steps.append(f"llm_learning:{c}_edges")

        if intent.kind == "greeting":
            return QueryResponse(
                answer="Hello! How can I help you today?",
                raw_text=encoded.raw_text,
                source=None,
                target=None,
                used_fallback=False,
                created_edges=created_edges,
                confidence=1.0,
                node_path=[],
                steps=steps + ["decode:greeting"],
                encoder_backend=encoded.backend,
                activation_ranges=profile.active_ranges,
                active_dims=profile.active_dims,
                shortcut_applied=profile.shortcut_applied,
                expansion_node_id=None,
                new_nodes_created=new_nodes,
            )

        if intent.kind == "relation" and intent.source and intent.target:
            res = self._run_relation(
                encoded,
                profile=profile,
                source=intent.source,
                target=intent.target,
                max_hops=max_hops,
                max_paths=max_paths,
                steps=steps,
                allow_learning=allow_learning,
            )
            res.created_edges += created_edges
            res.new_nodes_created += new_nodes
            return res

        if intent.kind == "concept" and intent.concept:
            res = self._run_concept(
                encoded,
                profile=profile,
                concept=intent.concept,
                steps=steps,
                allow_learning=allow_learning,
            )
            res.created_edges += created_edges
            res.new_nodes_created += new_nodes
            return res

        if intent.kind == "personal_fact" and intent.personal_attribute and intent.personal_value:
            res = self._run_personal_fact(
                encoded,
                profile=profile,
                attribute=intent.personal_attribute,
                value=intent.personal_value,
                steps=steps,
                allow_learning=allow_learning,
            )
            res.created_edges += created_edges
            res.new_nodes_created += new_nodes
            return res

        if intent.kind == "personal_query" and intent.personal_attribute:
            res = self._run_personal_query(
                encoded,
                profile=profile,
                attribute=intent.personal_attribute,
                steps=steps,
            )
            res.created_edges += created_edges
            res.new_nodes_created += new_nodes
            return res

        if intent.kind == "general_fact" and intent.source and intent.target:
            res = self._run_general_fact(
                encoded,
                profile=profile,
                source=intent.source,
                target=intent.target,
                steps=steps,
                allow_learning=allow_learning,
            )
            res.created_edges += created_edges
            res.new_nodes_created += new_nodes
            return res

        return QueryResponse(
            answer="I can answer relation questions like 'does steam burn?' and concept questions like 'what is fire?'.",
            raw_text=encoded.raw_text,
            source=None,
            target=None,
            used_fallback=False,
            created_edges=0,
            confidence=0.0,
            node_path=[],
            steps=steps + ["decode:unsupported"],
            encoder_backend=encoded.backend,
            activation_ranges=profile.active_ranges,
            active_dims=profile.active_dims,
            shortcut_applied=profile.shortcut_applied,
            expansion_node_id=None,
            new_nodes_created=0,
        )

    def _parse_intent(self, raw_text: str) -> QueryIntent:
        for pattern, attribute in self.personal_patterns:
            match = pattern.match(raw_text)
            if match:
                value = normalize_label(match.group(1))
                if value:
                    return QueryIntent(
                        kind="personal_fact",
                        personal_attribute=attribute,
                        personal_value=value,
                    )

        generic_fact = self.personal_fact_generic_pattern.match(raw_text)
        if generic_fact:
            attribute = normalize_label(generic_fact.group(1))
            value = normalize_label(generic_fact.group(2))
            if attribute and value:
                return QueryIntent(
                    kind="personal_fact",
                    personal_attribute=attribute,
                    personal_value=value,
                )

        for pattern, attribute in self.personal_query_patterns:
            if pattern.match(raw_text):
                return QueryIntent(
                    kind="personal_query",
                    personal_attribute=attribute,
                )

        generic_personal_query = self.personal_query_generic_pattern.match(raw_text)
        if generic_personal_query:
            attribute = normalize_label(generic_personal_query.group(1))
            if attribute:
                return QueryIntent(
                    kind="personal_query",
                    personal_attribute=attribute,
                )

        for pattern in self.relation_patterns:
            match = pattern.match(raw_text)
            if match:
                return QueryIntent(
                    kind="relation",
                    source=normalize_label(match.group(1)),
                    target=normalize_label(match.group(2)),
                )
        for pattern in self.concept_patterns:
            concept = pattern.match(raw_text)
            if concept:
                return QueryIntent(kind="concept", concept=normalize_label(concept.group(1)))
                
        general_fact_match = self.general_fact_pattern.match(raw_text)
        if general_fact_match:
            subject = normalize_label(general_fact_match.group(1))
            obj = normalize_label(general_fact_match.group(2))
            if subject and obj and subject not in ("what", "who", "where", "when", "why", "how", "which"):
                return QueryIntent(
                    kind="general_fact",
                    source=subject,
                    target=obj,
                )

        return QueryIntent(kind="unknown")

    def _run_relation(
        self,
        encoded: EncodedQuery,
        *,
        profile: ActivationProfile,
        source: str,
        target: str,
        max_hops: int,
        max_paths: int,
        steps: list[str],
        allow_learning: bool,
    ) -> QueryResponse:
        source_exists = self.graph.node_exists(source)
        target_exists = self.graph.node_exists(target)
        steps.append(f"bloom:{int(source_exists)}/{int(target_exists)}")

        paths = self.graph.find_paths(source, target, max_hops=max_hops, max_paths=max_paths)
        steps.append(f"traverse:{len(paths)}")
        if paths:
            top = paths[0]
            if allow_learning:
                for edge_id in top.edge_ids:
                    self.graph.strengthen_edge(edge_id)
            return QueryResponse(
                answer=self.decoder.decode_path(top),
                raw_text=encoded.raw_text,
                source=source,
                target=target,
                used_fallback=False,
                created_edges=0,
                confidence=max(0.0, min(1.0, top.score)),
                node_path=top.node_labels,
                steps=steps + ["decode:path"],
                encoder_backend=encoded.backend,
                activation_ranges=profile.active_ranges,
                active_dims=profile.active_dims,
                shortcut_applied=profile.shortcut_applied,
                expansion_node_id=None,
                new_nodes_created=0,
            )

        created = 0
        new_nodes: set[str] = set()
        expansion_node_id = None
        if allow_learning and self.expansion_queue is not None:
            expansion_node = self.expansion_queue.enqueue(encoded.raw_text, source, target)
            expansion_node_id = expansion_node.id
            steps.append("expansion:queued")

        if allow_learning and self.expansion_resolver is not None:
            resolved_now, connector_name = self.expansion_resolver.resolve_relation(source, target)
            if resolved_now > 0:
                created += resolved_now
                if connector_name:
                    steps.append(f"external:{connector_name}")
                if expansion_node_id is not None and self.expansion_queue is not None:
                    self.expansion_queue.mark_resolved(expansion_node_id, created_edges=resolved_now, provenance=connector_name or "external")
                if not source_exists and self.graph.node_exists(source):
                    new_nodes.add(source)
                if not target_exists and self.graph.node_exists(target):
                    new_nodes.add(target)

                paths_external = self.graph.find_paths(source, target, max_hops=max_hops, max_paths=max_paths)
                if paths_external:
                    top = paths_external[0]
                    return QueryResponse(
                        answer=self.decoder.decode_path(top),
                        raw_text=encoded.raw_text,
                        source=source,
                        target=target,
                        used_fallback=True,
                        created_edges=created,
                        confidence=max(0.0, min(1.0, top.score)),
                        node_path=top.node_labels,
                        steps=steps + ["decode:external"],
                        encoder_backend=encoded.backend,
                        activation_ranges=profile.active_ranges,
                        active_dims=profile.active_dims,
                        shortcut_applied=profile.shortcut_applied,
                        expansion_node_id=expansion_node_id,
                        new_nodes_created=len(new_nodes),
                    )

        fallback_edges = self._fallback_edges(source, target) if allow_learning else []
        if fallback_edges:
            for s, t, edge_type, strength in fallback_edges:
                if not self.graph.node_exists(s):
                    new_nodes.add(s)
                if not self.graph.node_exists(t):
                    new_nodes.add(t)
                self.graph.create_edge(
                    s,
                    t,
                    edge_type,
                    strength=strength,
                    vector=self._build_edge_vector(encoded.semantic_vector, edge_type, profile),
                )
                created += 1
            steps.append("fallback:learned")
        elif not allow_learning:
            steps.append("learning:disabled")
        else:
            steps.append("fallback:none")

        if created == 0 and allow_learning and self.expansion_resolver is not None:
            resolved = self.expansion_resolver.resolve_pending(max_items=1)
            steps.append("expansion:resolved" if resolved > 0 else "expansion:pending")

        paths_after = self.graph.find_paths(source, target, max_hops=max_hops, max_paths=max_paths)
        if paths_after:
            top = paths_after[0]
            return QueryResponse(
                answer=self.decoder.decode_path(top),
                raw_text=encoded.raw_text,
                source=source,
                target=target,
                used_fallback=True,
                created_edges=created,
                confidence=max(0.0, min(1.0, top.score)),
                node_path=top.node_labels,
                steps=steps + ["decode:post-fallback"],
                encoder_backend=encoded.backend,
                activation_ranges=profile.active_ranges,
                active_dims=profile.active_dims,
                shortcut_applied=profile.shortcut_applied,
                expansion_node_id=expansion_node_id,
                new_nodes_created=len(new_nodes),
            )

        return QueryResponse(
            answer=f"I do not know this yet: {source} -> {target}. I have queued external research and will learn this automatically.",
            raw_text=encoded.raw_text,
            source=source,
            target=target,
            used_fallback=True,
            created_edges=created,
            confidence=0.0,
            node_path=[source],
            steps=steps + ["decode:unknown"],
            encoder_backend=encoded.backend,
            activation_ranges=profile.active_ranges,
            active_dims=profile.active_dims,
            shortcut_applied=profile.shortcut_applied,
            expansion_node_id=expansion_node_id,
            new_nodes_created=len(new_nodes),
        )

    def _run_concept(
        self,
        encoded: EncodedQuery,
        *,
        profile: ActivationProfile,
        concept: str,
        steps: list[str],
        allow_learning: bool,
    ) -> QueryResponse:
        neighbors = self.graph.get_neighbors(concept)
        ranked = sorted(neighbors, key=lambda edge: edge.strength, reverse=True)[:3]
        created = 0
        new_nodes = 0
        used_fallback = False

        if not ranked and allow_learning and self.expansion_resolver is not None:
            concept_exists_before = self.graph.node_exists(concept)
            created, connector_name = self.expansion_resolver.resolve_concept(concept)
            if created > 0:
                used_fallback = True
                if connector_name:
                    steps.append(f"external_concept:{connector_name}")
                ranked = sorted(self.graph.get_neighbors(concept), key=lambda edge: edge.strength, reverse=True)[:3]
                if not concept_exists_before and self.graph.node_exists(concept):
                    new_nodes = 1

        summary_items = []
        for edge in ranked:
            summary_items.append((self.graph.get_node_label(edge.target), edge.type, edge.strength))
        answer = self.decoder.decode_concept(concept, summary_items)
        node_path = [concept] + [item[0] for item in summary_items]
        confidence = 0.0 if not ranked else min(1.0, sum(edge.strength for edge in ranked) / len(ranked))
        return QueryResponse(
            answer=answer,
            raw_text=encoded.raw_text,
            source=concept,
            target=None,
            used_fallback=used_fallback,
            created_edges=created,
            confidence=confidence,
            node_path=node_path,
            steps=steps + [f"concept_neighbors:{len(ranked)}", "decode:concept"],
            encoder_backend=encoded.backend,
            activation_ranges=profile.active_ranges,
            active_dims=profile.active_dims,
            shortcut_applied=profile.shortcut_applied,
            expansion_node_id=None,
            new_nodes_created=new_nodes,
        )

    def _run_personal_fact(
        self,
        encoded: EncodedQuery,
        *,
        profile: ActivationProfile,
        attribute: str,
        value: str,
        steps: list[str],
        allow_learning: bool,
    ) -> QueryResponse:
        created = 0
        new_nodes = 0
        if allow_learning:
            self_exists_before = self.graph.node_exists("self")
            memory_label = f"{attribute} {value}"
            memory_exists_before = self.graph.node_exists(memory_label)
            self.graph.create_edge(
                "self",
                memory_label,
                EdgeType.CORRELATES,
                strength=0.95,
                vector=self._build_edge_vector(encoded.semantic_vector, EdgeType.CORRELATES, profile),
            )
            created = 1
            if not self_exists_before:
                new_nodes += 1
            if not memory_exists_before:
                new_nodes += 1
            steps.append("personal:stored")
        else:
            steps.append("learning:disabled")

        answer = f"Noted. I will remember your {attribute}: {value}."
        return QueryResponse(
            answer=answer,
            raw_text=encoded.raw_text,
            source="self",
            target=f"{attribute} {value}",
            used_fallback=False,
            created_edges=created,
            confidence=0.99 if created else 0.0,
            node_path=["self", f"{attribute} {value}"] if created else ["self"],
            steps=steps + ["decode:personal"],
            encoder_backend=encoded.backend,
            activation_ranges=profile.active_ranges,
            active_dims=profile.active_dims,
            shortcut_applied=profile.shortcut_applied,
            expansion_node_id=None,
            new_nodes_created=new_nodes,
        )

    def _run_personal_query(
        self,
        encoded: EncodedQuery,
        *,
        profile: ActivationProfile,
        attribute: str,
        steps: list[str],
    ) -> QueryResponse:
        alias_map: dict[str, tuple[str, ...]] = {
            "name": ("name", "identity"),
            "identity": ("identity", "name"),
            "nationality": ("nationality", "country", "citizenship", "from"),
            "location": ("location",),
            "work": ("work", "workplace", "company"),
            "preference": ("preference", "like", "likes"),
            "email": ("email",),
            "phone": ("phone",),
            "address": ("address",),
        }
        aliases = alias_map.get(attribute, (attribute,))
        neighbors = self.graph.get_neighbors("self")

        best_value = ""
        best_target = ""
        best_strength = 0.0
        for edge in neighbors:
            target_label = self.graph.get_node_label(edge.target)
            for alias in aliases:
                prefix = alias + " "
                if target_label.startswith(prefix):
                    candidate_value = target_label[len(prefix) :].strip()
                    if candidate_value and edge.strength >= best_strength:
                        best_strength = edge.strength
                        best_value = candidate_value
                        best_target = target_label
                    break

        # Generic fallback for any attribute stored via personal_fact_generic_pattern
        if not best_value:
            prefix = attribute + " "
            for edge in neighbors:
                target_label = self.graph.get_node_label(edge.target)
                if target_label.startswith(prefix):
                    candidate_value = target_label[len(prefix) :].strip()
                    if candidate_value and edge.strength >= best_strength:
                        best_strength = edge.strength
                        best_value = candidate_value
                        best_target = target_label

        if best_value:
            answer = f"Your {attribute} is {best_value}."
            return QueryResponse(
                answer=answer,
                raw_text=encoded.raw_text,
                source="self",
                target=best_target,
                used_fallback=False,
                created_edges=0,
                confidence=min(1.0, best_strength),
                node_path=["self", best_target],
                steps=steps + ["personal:retrieved", "decode:personal-query"],
                encoder_backend=encoded.backend,
                activation_ranges=profile.active_ranges,
                active_dims=profile.active_dims,
                shortcut_applied=profile.shortcut_applied,
                expansion_node_id=None,
                new_nodes_created=0,
            )

        return QueryResponse(
            answer=f"I do not have your {attribute} in personal memory yet.",
            raw_text=encoded.raw_text,
            source="self",
            target=attribute,
            used_fallback=False,
            created_edges=0,
            confidence=0.0,
            node_path=["self"],
            steps=steps + ["personal:missing", "decode:personal-query"],
            encoder_backend=encoded.backend,
            activation_ranges=profile.active_ranges,
            active_dims=profile.active_dims,
            shortcut_applied=profile.shortcut_applied,
            expansion_node_id=None,
            new_nodes_created=0,
        )

    def _fallback_edges(self, source: str, target: str) -> list[tuple[str, str, EdgeType, float]]:
        rules: dict[tuple[str, str], list[tuple[str, str, EdgeType, float]]] = {
            ("steam", "burn"): [
                ("steam", "heat", EdgeType.IS_A, 0.84),
                ("heat", "burn", EdgeType.CAUSES, 0.90),
            ],
            ("fire", "burn"): [
                ("fire", "heat", EdgeType.IS_A, 0.91),
                ("heat", "burn", EdgeType.CAUSES, 0.90),
            ],
            ("ice", "cold"): [("ice", "cold", EdgeType.IS_A, 0.88)],
        }
        key = (source, target)
        if key in rules:
            return rules[key]
        if target in {"burn", "hurt"} and source in {"fire", "steam", "acid"}:
            return [(source, "heat", EdgeType.CORRELATES, 0.72), ("heat", target, EdgeType.CAUSES, 0.78)]
        return []

    def _build_edge_vector(self, semantic_700: list[float], edge_type: EdgeType, profile: ActivationProfile) -> list[float]:
        vector = [0.0] * 1024
        for idx, value in enumerate(semantic_700[:700]):
            vector[idx] = float(value)

        type_dim = {
            EdgeType.CAUSES: 640,
            EdgeType.CORRELATES: 641,
            EdgeType.IS_A: 642,
            EdgeType.TEMPORAL: 643,
            EdgeType.INFERRED: 644,
        }[edge_type]
        vector[type_dim] = 1.0

        vector[700] = min(1.0, profile.expand_rate)
        vector[800] = profile.active_dims / 324.0
        vector[850] = profile.learning_rate
        vector[900] = profile.decay_rate
        vector[950] = 0.7 if profile.shortcut_applied else 0.4
        vector[1000] = 1.0
        return vector

    def _run_general_fact(
        self,
        encoded: EncodedQuery,
        *,
        profile: ActivationProfile,
        source: str,
        target: str,
        steps: list[str],
        allow_learning: bool,
    ) -> QueryResponse:
        created = 0
        new_nodes = 0
        if allow_learning:
            source_exists = self.graph.node_exists(source)
            target_exists = self.graph.node_exists(target)
            
            self.graph.create_edge(
                source,
                target,
                EdgeType.IS_A,
                strength=0.95,
                vector=self._build_edge_vector(encoded.semantic_vector, EdgeType.IS_A, profile),
            )
            self.graph.create_edge(
                target,
                source,
                EdgeType.CORRELATES,
                strength=0.95,
                vector=self._build_edge_vector(encoded.semantic_vector, EdgeType.CORRELATES, profile),
            )
            created = 2
            if not source_exists:
                new_nodes += 1
            if not target_exists:
                new_nodes += 1
            steps.append("general_fact:stored")
        else:
            steps.append("learning:disabled")

        answer = f"Noted. I will remember that {source} is {target}."
        return QueryResponse(
            answer=answer,
            raw_text=encoded.raw_text,
            source=source,
            target=target,
            used_fallback=False,
            created_edges=created,
            confidence=0.99 if created else 0.0,
            node_path=[source, target] if created else [source],
            steps=steps + ["decode:general_fact"],
            encoder_backend=encoded.backend,
            activation_ranges=profile.active_ranges,
            active_dims=profile.active_dims,
            shortcut_applied=profile.shortcut_applied,
            expansion_node_id=None,
            new_nodes_created=new_nodes,
        )

    def _apply_llm_edges(self, edges: list[dict], encoded: EncodedQuery, profile: ActivationProfile) -> tuple[int, int]:
        created = 0
        new_nodes = 0
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            rel_str = edge["relation"]
            try:
                etype = EdgeType[rel_str]
            except (KeyError, ValueError):
                etype = EdgeType.CORRELATES

            source_exists = self.graph.node_exists(source)
            target_exists = self.graph.node_exists(target)

            self.graph.create_edge(
                source,
                target,
                etype,
                strength=0.92,
                vector=self._build_edge_vector(encoded.semantic_vector, etype, profile),
            )
            created += 1
            if not source_exists:
                new_nodes += 1
            if not target_exists:
                new_nodes += 1
        return created, new_nodes


