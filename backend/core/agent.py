"""
core/agent.py — The high-level Paragi API.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from .kernel import CognitiveKernel
from .orchestrator import CognitiveOrchestrator


class ParagiAgent:
    """
    Primary interface for the Paragi cognitive runtime.
    """

    def __init__(self) -> None:
        self.kernel = CognitiveKernel()
        self.orchestrator = CognitiveOrchestrator(self.kernel)
        
        # Start background cognition
        self.kernel.startup()

    def query(self, text: str, user_id: str = "guest") -> Dict[str, Any]:
        """Process a natural language query."""
        return self.orchestrator.process_query(text, user_id=user_id)

    def shutdown(self) -> None:
        """Shutdown the agent and its resources."""
        self.kernel.shutdown()
