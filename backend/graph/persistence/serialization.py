"""graph/persistence/serialization.py — JSON serialization for graph snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.types import EdgeRecord, NodeRecord


def serialize_node(node: NodeRecord) -> Dict[str, Any]:
    return {
        "id": node.id, "label": node.label,
        "created": node.created, "last_accessed": node.last_accessed,
        "access_count": node.access_count,
    }


def serialize_edge(edge: EdgeRecord) -> Dict[str, Any]:
    return {
        "id": edge.id, "source": edge.source, "target": edge.target,
        "type": edge.type, "strength": edge.strength,
        "emotional_weight": edge.emotional_weight, "recall_count": edge.recall_count,
        "stability": edge.stability, "last_activated": edge.last_activated,
        "created": edge.created, "confidence": edge.confidence,
        # Skip vector for readability; include if needed
    }


def export_graph_json(nodes: list, edges: list, path: Path) -> None:
    """Export graph snapshot to JSON file."""
    data = {
        "nodes": [serialize_node(n) for n in nodes],
        "edges": [serialize_edge(e) for e in edges],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def import_graph_json(path: Path) -> Dict[str, Any]:
    """Import graph snapshot from JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))
