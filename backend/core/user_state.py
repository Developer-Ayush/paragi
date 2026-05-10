"""
core/user_state.py — The Cognitive Economy Ledger (§6.2).
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from core.logger import get_logger

log = get_logger(__name__)


class UserStateManager:
    """
    Manages user profiles, cognitive credits, and quotas.
    """

    def __init__(self) -> None:
        # In-memory for now, can be linked to a DB
        self._users: Dict[str, Dict[str, Any]] = {}

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Fetch or initialize a user profile."""
        if user_id not in self._users:
            self._users[user_id] = {
                "user_id": user_id,
                "credits": 100, # Starting credits
                "tier": "free",
                "contributions": 0,
                "profile": {}
            }
        return self._users[user_id]

    def award_credits(self, user_id: str, amount: int, reason: str = "") -> int:
        """Award credits for graph contributions."""
        user = self.get_user(user_id)
        user["credits"] += amount
        user["contributions"] += 1
        log.info(f"Awarded {amount} credits to {user_id}. Reason: {reason}")
        return user["credits"]

    def spend_credits(self, user_id: str, amount: int) -> bool:
        """Spend credits for reasoning operations."""
        user = self.get_user(user_id)
        if user["credits"] >= amount:
            user["credits"] -= amount
            return True
        return False

    def update_profile(self, user_id: str, key: str, value: Any) -> None:
        """Update non-graph user metadata."""
        user = self.get_user(user_id)
        user["profile"][key] = value
