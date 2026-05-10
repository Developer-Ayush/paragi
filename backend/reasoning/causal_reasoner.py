"""reasoning/causal_reasoner.py — Causal reasoning via graph path consensus."""
from __future__ import annotations
from core.semantic_ir import SemanticIR
from core.constants import EDGE_RELATION_TEXT
from graph.graph import GraphEngine
from .scorer import score_paths, summarize_paths
from .confidence import compute_path_confidence


def causal_reason(graph: GraphEngine, ir: SemanticIR, source: str, target: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    consensus = graph.path_consensus(source, target, max_hops=7, max_paths=64)
    paths = graph.find_paths(source, target, max_hops=7, max_paths=64,
                             edge_type_filter=["CAUSES", "CORRELATES", "TEMPORAL"])
    confidence = compute_path_confidence(paths)
    node_path = paths[0].node_labels if paths else [source, target]

    if consensus.path_count == 0:
        return ReasoningResult(answer="", confidence=0.0, node_path=[source, target],
                               mode="causal", used_fallback=True)

    relation = EDGE_RELATION_TEXT.get(consensus.inferred_type.value if hasattr(consensus.inferred_type, "value") else str(consensus.inferred_type), "is related to")
    answer = f"{source} {relation} {target}"
    if consensus.path_count > 1:
        answer += f" (supported by {consensus.path_count} reasoning paths)"
    return ReasoningResult(
        answer=answer, confidence=confidence, paths=paths,
        node_path=node_path, mode="causal",
        extra={"path_count": consensus.path_count, "inferred_type": str(consensus.inferred_type)},
    )
