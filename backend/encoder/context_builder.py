"""encoder/context_builder.py — Build context dict for SemanticIR from session state."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_context(
    *,
    user_id: str = "guest",
    chat_id: Optional[str] = None,
    scope: str = "main",
    domain: str = "general",
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    user_state: Optional[Dict[str, Any]] = None,
    working_memory: Optional[List[str]] = None,
    is_realtime: bool = False,
) -> Dict[str, Any]:
    """
    Assemble the context dictionary stored in SemanticIR.context.

    This context flows through the entire pipeline, providing the reasoning
    engine and decoder with session/user-level information.
    """
    ctx: Dict[str, Any] = {
        "user_id": user_id,
        "chat_id": chat_id,
        "scope": scope,
        "domain": domain,
        "is_realtime": is_realtime,
    }

    if conversation_history:
        # Include only last 5 turns to keep context compact
        ctx["recent_turns"] = conversation_history[-5:]

    if user_state:
        ctx["user_state"] = user_state

    if working_memory:
        ctx["working_memory"] = working_memory[:10]

    return ctx
