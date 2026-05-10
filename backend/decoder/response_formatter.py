from typing import Any, Dict
from reasoning.engine import ReasoningResult

class ResponseFormatter:
    """
    Formats ReasoningResult and SemanticIR into final user-facing responses.
    """
    def format(self, result: ReasoningResult, ir: Any) -> Dict[str, Any]:
        return {
            "answer": result.answer,
            "confidence": round(result.confidence, 4),
            "mode": result.mode,
            "node_path": result.node_path,
            "metadata": {
                "intent": ir.intent,
                "domain": result.domain,
                "scope": result.scope
            }
        }

def format_response(result: ReasoningResult, ir: Any) -> Dict[str, Any]:
    return ResponseFormatter().format(result, ir)
