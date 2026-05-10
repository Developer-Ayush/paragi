"""graph/activation/salience.py — Salience decay modeling."""
from __future__ import annotations
import math
import time
from typing import Dict


def compute_salience(
    activation_map: Dict[str, float],
    last_accessed: Dict[str, float],
    *,
    decay_hours: float = 24.0,
) -> Dict[str, float]:
    """
    Apply temporal salience decay to activation levels.
    Nodes not accessed recently have reduced salience.
    """
    now = time.time()
    result: Dict[str, float] = {}
    for label, level in activation_map.items():
        last = last_accessed.get(label, now)
        age_hours = (now - last) / 3600.0
        if decay_hours > 0:
            decay_factor = math.exp(-age_hours / decay_hours)
        else:
            decay_factor = 1.0
        result[label] = level * decay_factor
    return result
