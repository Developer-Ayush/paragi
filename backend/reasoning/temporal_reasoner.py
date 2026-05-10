"""reasoning/temporal_reasoner.py — Temporal reasoning via TEMPORAL/SEQUENCE edges."""
from __future__ import annotations
from core.semantic_ir import SemanticIR
from graph.graph import GraphEngine
from graph.temporal import build_timeline, causal_temporal_chain
from .confidence import compute_path_confidence


def temporal_reason(graph: GraphEngine, ir: SemanticIR, source: str, target: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    paths = causal_temporal_chain(graph, source, target)
    timeline = build_timeline(graph, source)
    confidence = compute_path_confidence(paths)
    node_path = paths[0].node_labels if paths else timeline[:3] if timeline else [source, target]

    if not paths and not timeline:
        return ReasoningResult(answer="", confidence=0.0, node_path=[source, target],
                               mode="temporal", used_fallback=True)

    if timeline and len(timeline) > 1:
        answer = " → ".join(timeline[:6])
    elif paths:
        answer = " → ".join(paths[0].node_labels)
    else:
        answer = f"{source} precedes {target}"
    return ReasoningResult(
        answer=answer, confidence=max(confidence, 0.35),
        paths=paths, node_path=node_path, mode="temporal",
        extra={"timeline": timeline},
    )
