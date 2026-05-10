"""decoder/response_formatter.py — Format the final API response dict."""
from __future__ import annotations
from typing import Any, Dict, List


def format_response(
    *,
    answer: str,
    confidence: float,
    node_path: List[str],
    reasoning_mode: str,
    query_type: str,
    llm_used: bool = False,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the JSON response dict returned by POST /query."""
    return {
        "answer": answer,
        "confidence": round(confidence, 4),
        "node_path": node_path,
        "reasoning_mode": reasoning_mode,
        "query_type": query_type,
        "llm_used": llm_used,
        **(extra or {}),
    }
