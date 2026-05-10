"""reasoning/meta_reasoner.py — Meta-level conflict resolution and strategy refinement."""
from __future__ import annotations

from typing import List
from .engine import ReasoningResult


class MetaReasoner:
    """
    Evaluates and reconciles multiple reasoning results.
    
    Architectural Role:
    The self-monitoring layer of the reasoning engine. If multiple reasoners yield 
    conflicting answers (e.g., Causal vs. Contradiction), the MetaReasoner 
    resolves the conflict using structural evidence and confidence weightings.
    """

    def resolve_conflicts(self, results: List[ReasoningResult]) -> ReasoningResult:
        """
        Takes a list of results (possibly from different modes) and returns the most coherent one.
        """
        if not results:
            return ReasoningResult(answer="No reasoning results to evaluate.", confidence=0.0, mode="meta")

        # Sort by confidence
        sorted_results = sorted(results, key=lambda x: -x.confidence)
        
        # Check for sharp contradictions (e.g., one result says yes, another says no via CONTRADICTS edges)
        # For now, we use a weighted majority/highest-confidence heuristic
        best_result = sorted_results[0]
        
        # If the best result has low confidence but we have many low-confidence results 
        # pointing in the same direction, we could boost it.
        
        # Refine the answer if it's a meta-resolution
        if len(results) > 1 and best_result.confidence > 0.5:
            # Check if there's a runner-up that significantly disagrees
            runner_up = sorted_results[1]
            if runner_up.confidence > 0.3 and self._is_contradictory(best_result, runner_up):
                best_result.answer += f" (Note: There is a secondary {runner_up.mode} signal suggesting a potential conflict with {runner_up.confidence:.2f} confidence.)"
        
        return best_result

    def _is_contradictory(self, r1: ReasoningResult, r2: ReasoningResult) -> bool:
        """Simple heuristic for identifying contradictions in results."""
        # In a real system, this would look at CONTRADICTS edges in the paths
        negations = ["not", "never", "no", "contradict", "conflict"]
        s1 = r1.answer.lower()
        s2 = r2.answer.lower()
        
        # Check if one contains a negation and the other doesn't
        has_neg1 = any(n in s1 for n in negations)
        has_neg2 = any(n in s2 for n in negations)
        
        return has_neg1 != has_neg2
