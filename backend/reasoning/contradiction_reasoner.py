"""reasoning/contradiction_reasoner.py — Contradiction detection and resolution."""
from __future__ import annotations
from core.semantic_ir import SemanticIR
from graph.graph import GraphEngine
from graph.contradiction import detect_contradiction


def contradiction_reason(graph: GraphEngine, ir: SemanticIR, source: str, target: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    # Use source as the disputed concept and target as one side
    neighbors = graph.get_neighbors(source)
    targets = [graph.get_node_label(e.target) for e in neighbors if e.type == "CONTRADICTS"]
    if not targets:
        targets = [target]

    result = detect_contradiction(graph, source, target, targets[0] if targets else target)
    answer = f"On '{source}': {result.verdict} is supported by {result.positive_paths} vs {result.negative_paths} paths."
    return ReasoningResult(
        answer=answer, confidence=result.confidence,
        node_path=[source, target], mode="contradiction",
        extra={"verdict": result.verdict, "confidence": result.confidence},
    )


"""reasoning/planning_reasoner.py — Planning via GOAL/DEPENDS_ON edge traversal."""


def planning_reason(graph: GraphEngine, ir: SemanticIR, source: str) -> "ReasoningResult":  # noqa
    from .engine import ReasoningResult
    node = graph.get_node_by_label(source)
    if node is None:
        return ReasoningResult(answer="", confidence=0.0, mode="planning", used_fallback=True)

    steps = [source]
    visited = {node.id}
    current_id = node.id
    for _ in range(6):
        edges = [e for e in graph.store.list_outgoing(current_id)
                 if e.type in ("GOAL", "DEPENDS_ON") and e.target not in visited]
        if not edges:
            break
        best = max(edges, key=lambda e: e.strength)
        label = graph.get_node_label(best.target)
        steps.append(label)
        visited.add(best.target)
        current_id = best.target

    if len(steps) <= 1:
        return ReasoningResult(answer="", confidence=0.0, mode="planning", used_fallback=True)

    answer = "Steps: " + " → ".join(steps)
    return ReasoningResult(answer=answer, confidence=0.65, node_path=steps, mode="planning")
