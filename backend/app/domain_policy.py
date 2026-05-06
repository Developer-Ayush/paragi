from __future__ import annotations

from typing import Iterable


DOMAIN_CREDIT_MULTIPLIERS: dict[str, float] = {
    "general": 1.0,
    "medical": 2.0,
    "legal": 1.8,
    "physics": 1.6,
    "finance": 1.4,
    "technology": 1.3,
}


DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "medical": {
        "doctor",
        "patient",
        "disease",
        "symptom",
        "treatment",
        "therapy",
        "medicine",
        "drug",
        "dose",
        "insulin",
        "glucose",
        "cancer",
        "virus",
        "bacteria",
        "hospital",
        "clinical",
    },
    "legal": {
        "law",
        "legal",
        "contract",
        "agreement",
        "court",
        "judge",
        "lawsuit",
        "liability",
        "rights",
        "plaintiff",
        "defendant",
        "statute",
        "regulation",
        "compliance",
    },
    "physics": {
        "physics",
        "force",
        "mass",
        "energy",
        "quantum",
        "gravity",
        "acceleration",
        "velocity",
        "motion",
        "thermodynamics",
        "electron",
        "photon",
        "relativity",
    },
    "finance": {
        "finance",
        "stock",
        "market",
        "investment",
        "portfolio",
        "revenue",
        "profit",
        "inflation",
        "interest",
        "loan",
        "debt",
        "capital",
        "valuation",
    },
    "technology": {
        "technology",
        "software",
        "code",
        "coding",
        "algorithm",
        "database",
        "api",
        "server",
        "network",
        "cloud",
        "python",
        "javascript",
        "ai",
        "machine",
        "learning",
    },
}


def normalize_domain(domain: str | None) -> str:
    if not domain:
        return "general"
    clean = domain.strip().lower()
    if clean in DOMAIN_CREDIT_MULTIPLIERS:
        return clean
    return "general"


def credit_multiplier(domain: str | None) -> float:
    return DOMAIN_CREDIT_MULTIPLIERS[normalize_domain(domain)]


def detect_domain(*, text: str, tokens: Iterable[str]) -> str:
    token_set = {token.strip().lower() for token in tokens if token.strip()}
    if not token_set and text:
        token_set = set(text.lower().split())

    best_domain = "general"
    best_score = 0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = len(token_set.intersection(keywords))
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain if best_score > 0 else "general"


def available_domains() -> list[str]:
    return list(DOMAIN_CREDIT_MULTIPLIERS.keys())

