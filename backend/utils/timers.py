"""utils/timers.py — Performance timing utilities."""
import time
from core.types import now_ts

def perf_timer():
    return time.perf_counter()

def elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0

__all__ = ["now_ts", "perf_timer", "elapsed_ms"]
