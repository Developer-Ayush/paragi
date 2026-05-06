from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List

from .domain_policy import available_domains, credit_multiplier, normalize_domain

TIER_DAILY_QUOTA = {
    "free": 100,
    "paid": 2000,
    "contributor": 300,
}


def sanitize_user_id(user_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]", "_", (user_id or "").strip())
    normalized = normalized.strip("_")
    if not normalized:
        return "guest"
    return normalized[:64]


@dataclass(slots=True)
class UserProfile:
    user_id: str
    tier: str
    daily_quota: int
    query_used_today: int
    credit_balance: int
    credits_earned_total: int
    main_nodes_contributed: int
    last_reset_date: str
    domain_nodes_contributed: Dict[str, int] = field(default_factory=dict)
    domain_credits_earned: Dict[str, int] = field(default_factory=dict)


class UserStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._users: Dict[str, UserProfile] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        for user_id, raw in payload.items():
            try:
                profile = UserProfile(
                    user_id=str(raw["user_id"]),
                    tier=str(raw["tier"]),
                    daily_quota=int(raw["daily_quota"]),
                    query_used_today=int(raw["query_used_today"]),
                    credit_balance=int(raw["credit_balance"]),
                    credits_earned_total=int(raw["credits_earned_total"]),
                    main_nodes_contributed=int(raw["main_nodes_contributed"]),
                    last_reset_date=str(raw["last_reset_date"]),
                    domain_nodes_contributed=self._parse_int_map(raw.get("domain_nodes_contributed", {})),
                    domain_credits_earned=self._parse_int_map(raw.get("domain_credits_earned", {})),
                )
                self._users[user_id] = profile
            except Exception:
                continue

    def _parse_int_map(self, payload: object) -> Dict[str, int]:
        if not isinstance(payload, dict):
            return {}
        result: Dict[str, int] = {}
        for key, value in payload.items():
            try:
                result[str(key)] = int(value)
            except Exception:
                continue
        return result

    def _save(self) -> None:
        payload = {user_id: asdict(profile) for user_id, profile in self._users.items()}
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def _today(self) -> str:
        return date.today().isoformat()

    def _ensure_fresh_day(self, profile: UserProfile) -> None:
        today = self._today()
        if profile.last_reset_date != today:
            profile.query_used_today = 0
            profile.last_reset_date = today

    def ensure_user(self, user_id: str, tier: str = "free") -> UserProfile:
        safe_id = sanitize_user_id(user_id)
        with self._lock:
            existing = self._users.get(safe_id)
            if existing is not None:
                self._ensure_fresh_day(existing)
                self._save()
                return existing

            tier_name = tier if tier in TIER_DAILY_QUOTA else "free"
            profile = UserProfile(
                user_id=safe_id,
                tier=tier_name,
                daily_quota=TIER_DAILY_QUOTA[tier_name],
                query_used_today=0,
                credit_balance=0,
                credits_earned_total=0,
                main_nodes_contributed=0,
                last_reset_date=self._today(),
                domain_nodes_contributed={},
                domain_credits_earned={},
            )
            self._users[safe_id] = profile
            self._save()
            return profile

    def register_user(self, user_id: str, tier: str = "free") -> UserProfile:
        safe_id = sanitize_user_id(user_id)
        with self._lock:
            tier_name = tier if tier in TIER_DAILY_QUOTA else "free"
            profile = self._users.get(safe_id)
            if profile is None:
                profile = self.ensure_user(safe_id, tier=tier_name)
            profile.tier = tier_name
            profile.daily_quota = TIER_DAILY_QUOTA[tier_name]
            self._ensure_fresh_day(profile)
            self._save()
            return profile

    def get_user(self, user_id: str) -> UserProfile:
        safe_id = sanitize_user_id(user_id)
        with self._lock:
            profile = self.ensure_user(safe_id)
            self._ensure_fresh_day(profile)
            self._save()
            return profile

    def consume_query(self, user_id: str) -> dict:
        with self._lock:
            profile = self.ensure_user(user_id)
            self._ensure_fresh_day(profile)

            if profile.query_used_today < profile.daily_quota:
                profile.query_used_today += 1
                self._save()
                return {
                    "allowed": True,
                    "from_credits": False,
                    "remaining_daily": profile.daily_quota - profile.query_used_today,
                    "credit_balance": profile.credit_balance,
                }

            if profile.credit_balance > 0:
                profile.credit_balance -= 1
                self._save()
                return {
                    "allowed": True,
                    "from_credits": True,
                    "remaining_daily": 0,
                    "credit_balance": profile.credit_balance,
                }

            self._save()
            return {
                "allowed": False,
                "from_credits": False,
                "remaining_daily": 0,
                "credit_balance": profile.credit_balance,
            }

    def award_main_graph_contribution(self, user_id: str, *, new_nodes_created: int, domain: str = "general") -> dict:
        domain_name = normalize_domain(domain)
        multiplier = credit_multiplier(domain_name)
        if new_nodes_created <= 0:
            profile = self.get_user(user_id)
            return {
                "awarded_credits": 0,
                "credit_balance": profile.credit_balance,
                "main_nodes_contributed": profile.main_nodes_contributed,
                "domain": domain_name,
                "domain_multiplier": multiplier,
                "domain_nodes_contributed": profile.domain_nodes_contributed.get(domain_name, 0),
                "domain_credits_earned": profile.domain_credits_earned.get(domain_name, 0),
            }

        with self._lock:
            profile = self.ensure_user(user_id)
            self._ensure_fresh_day(profile)
            awarded = int(round(int(new_nodes_created) * 10 * multiplier))
            profile.credit_balance += awarded
            profile.credits_earned_total += awarded
            profile.main_nodes_contributed += int(new_nodes_created)
            profile.domain_nodes_contributed[domain_name] = profile.domain_nodes_contributed.get(domain_name, 0) + int(new_nodes_created)
            profile.domain_credits_earned[domain_name] = profile.domain_credits_earned.get(domain_name, 0) + awarded

            if profile.tier == "free":
                profile.tier = "contributor"
                profile.daily_quota = TIER_DAILY_QUOTA["contributor"]

            self._save()
            return {
                "awarded_credits": awarded,
                "credit_balance": profile.credit_balance,
                "main_nodes_contributed": profile.main_nodes_contributed,
                "domain": domain_name,
                "domain_multiplier": multiplier,
                "domain_nodes_contributed": profile.domain_nodes_contributed.get(domain_name, 0),
                "domain_credits_earned": profile.domain_credits_earned.get(domain_name, 0),
            }

    def leaderboard(self, limit: int = 20) -> List[UserProfile]:
        safe_limit = max(1, min(100, int(limit)))
        with self._lock:
            items = list(self._users.values())
            items.sort(key=lambda p: (-p.main_nodes_contributed, -p.credits_earned_total, p.user_id))
            return items[:safe_limit]

    def leaderboard_by_domain(self, domain: str, limit: int = 20) -> List[UserProfile]:
        safe_limit = max(1, min(100, int(limit)))
        domain_name = normalize_domain(domain)
        with self._lock:
            items = [u for u in self._users.values() if u.domain_nodes_contributed.get(domain_name, 0) > 0]
            items.sort(
                key=lambda p: (
                    -p.domain_nodes_contributed.get(domain_name, 0),
                    -p.domain_credits_earned.get(domain_name, 0),
                    p.user_id,
                )
            )
            return items[:safe_limit]

    def domain_summary(self) -> list[dict]:
        with self._lock:
            summary: list[dict] = []
            for domain in available_domains():
                total_nodes = 0
                total_credits = 0
                contributor_count = 0
                for profile in self._users.values():
                    nodes = profile.domain_nodes_contributed.get(domain, 0)
                    credits = profile.domain_credits_earned.get(domain, 0)
                    if nodes > 0:
                        contributor_count += 1
                    total_nodes += nodes
                    total_credits += credits
                summary.append(
                    {
                        "domain": domain,
                        "total_nodes": total_nodes,
                        "total_credits": total_credits,
                        "contributors": contributor_count,
                    }
                )
            summary.sort(key=lambda d: (-d["total_nodes"], -d["total_credits"], d["domain"]))
            return summary
