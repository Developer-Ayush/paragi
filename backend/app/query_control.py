from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ActivationProfile:
    active_ranges: list[tuple[int, int]]
    active_dims: int
    expand_rate: float
    shortcut_applied: bool
    learning_rate: float
    decay_rate: float


class QueryClassifier:
    """Phase-4 query classifier and control-dim activation policy."""

    emotional_terms = {
        "sad",
        "angry",
        "fear",
        "afraid",
        "anxious",
        "depressed",
        "happy",
        "upset",
        "stress",
        "stressed",
        "lonely",
    }
    causal_terms = {"why", "cause", "causes", "because", "mechanism", "how"}
    factual_terms = {"what", "is", "does", "can", "who", "where", "when", "which", "define"}

    def classify(self, raw_text: str, tokens: list[str], recall_count: int) -> ActivationProfile:
        token_set = set(tokens)
        active_ranges: list[tuple[int, int]] = []

        if token_set.intersection(self.emotional_terms):
            active_ranges.append((175, 209))  # emotional state block
        if token_set.intersection(self.causal_terms):
            active_ranges.append((640, 669))  # causal / relational block
        if token_set.intersection(self.factual_terms):
            active_ranges.append((580, 639))  # factual world knowledge block
        if not active_ranges:
            active_ranges.append((580, 639))

        complexity = self._complexity_score(raw_text, tokens)
        target_dims = self._expand_dims(complexity, recall_count)
        shortcut_applied = recall_count >= 3
        expand_rate = min(1.0, target_dims / 324.0)
        learning_rate = self._learning_rate(recall_count)
        decay_rate = self._decay_rate(complexity)

        return ActivationProfile(
            active_ranges=active_ranges,
            active_dims=target_dims,
            expand_rate=expand_rate,
            shortcut_applied=shortcut_applied,
            learning_rate=learning_rate,
            decay_rate=decay_rate,
        )

    def _complexity_score(self, raw_text: str, tokens: list[str]) -> int:
        score = 0
        length = len(tokens)
        if length <= 4:
            score += 1
        elif length <= 10:
            score += 2
        else:
            score += 3

        causal_hits = len(set(tokens).intersection(self.causal_terms))
        score += min(2, causal_hits)
        if "?" in raw_text:
            score += 1
        return min(6, score)

    def _expand_dims(self, complexity: int, recall_count: int) -> int:
        # Baseline expansion by complexity, then shortcut collapse with repetition.
        base = {
            0: 16,
            1: 24,
            2: 48,
            3: 80,
            4: 120,
            5: 160,
            6: 200,
        }[complexity]
        if recall_count >= 10:
            return max(12, int(base * 0.35))
        if recall_count >= 5:
            return max(16, int(base * 0.55))
        if recall_count >= 3:
            return max(20, int(base * 0.70))
        return base

    def _learning_rate(self, recall_count: int) -> float:
        # Matches your idea: more recall => faster strengthening.
        if recall_count <= 0:
            return 0.10
        if recall_count == 1:
            return 0.18
        if recall_count <= 4:
            return 0.35
        if recall_count <= 9:
            return 0.60
        return 0.80

    def _decay_rate(self, complexity: int) -> float:
        # Slightly slower decay for high-complexity reasoning paths.
        return max(0.001, 0.010 - (complexity * 0.001))

