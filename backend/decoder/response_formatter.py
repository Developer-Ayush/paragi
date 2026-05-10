"""
decoder/response_formatter.py — Final output formatting and streaming.
"""
from __future__ import annotations

from typing import Dict, Any


class ResponseFormatter:
    """
    Handles final markdown polish and metadata wrapping.
    """

    def format(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wraps the raw text in a standardized response object with conversational polish.
        """
        mode = metadata.get("mode", "general")
        
        # Add a prefix based on the context if it's a raw graph chain
        if " -> " in text and not text.startswith("Hello") and not text.startswith("I don't"):
            if mode == "causal":
                text = f"I've traced this causal sequence: {text}"
            else:
                text = f"The knowledge graph indicates: {text}"
        
        return {
            "answer": text,
            "metadata": metadata,
            "status": "success"
        }
