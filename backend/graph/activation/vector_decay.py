"""
activation/vector_decay.py — Per-dimension vector decay (§3.2).
"""
from __future__ import annotations

from typing import List
from core.constants import (
    RANGE_EMOTIONAL_RANGE, RANGE_FACTUAL_WORLD, EDGE_DECAY_PER_CYCLE
)


def apply_vector_decay(vector: List[float], base_rate: float = EDGE_DECAY_PER_CYCLE) -> List[float]:
    """
    Applies differential decay rates to different dimensions of the cognitive vector.
    """
    decayed = list(vector)
    
    for i in range(len(decayed)):
        rate = base_rate
        
        # §3.2: Emotional states decay slower (0.1x base)
        if RANGE_EMOTIONAL_RANGE[0] <= i <= RANGE_EMOTIONAL_RANGE[1]:
            rate *= 0.1
            
        # §3.2: Factual knowledge decays faster (2.0x base)
        elif RANGE_FACTUAL_WORLD[0] <= i <= RANGE_FACTUAL_WORLD[1]:
            rate *= 2.0
            
        decayed[i] *= (1.0 - rate)
        
    return decayed
