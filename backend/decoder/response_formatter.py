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
        Wraps the raw text in a standardized response object.
        """
        return {
            "answer": text,
            "metadata": metadata,
            "status": "success"
        }
