from __future__ import annotations
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict

@dataclass
class MetricEntry:
    timestamp: float
    fallback_used: bool
    shortcut_formed: bool
    domain: str

class MetricsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_metric(self, fallback: bool, shortcut: bool, domain: str = "general") -> None:
        entry = MetricEntry(
            timestamp=time.time(),
            fallback_used=fallback,
            shortcut_formed=shortcut,
            domain=domain
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def get_summary(self, window_seconds: int = 3600) -> dict:
        now = time.time()
        start_time = now - window_seconds

        total = 0
        fallbacks = 0
        shortcuts = 0

        if not self.path.exists():
            return {"total_records": 0, "fallback_rate": 0.0, "shortcut_rate": 0.0, "window_seconds": window_seconds}

        # Optimization: Read only the end of the file if it's likely to be large
        # For simplicity in this prototype, we'll still read line by line but only process if within window
        # In a real system, we'd use a fixed-size buffer or a more efficient time-series store.
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                # Seek near the end if the file is large
                file_size = self.path.stat().st_size
                if file_size > 1_000_000: # 1MB
                    f.seek(file_size - 1_000_000)
                    # Skip the first (likely partial) line
                    f.readline()

                for line in f:
                    try:
                        data = json.loads(line)
                        if data["timestamp"] >= start_time:
                            total += 1
                            if data["fallback_used"]:
                                fallbacks += 1
                            if data["shortcut_formed"]:
                                shortcuts += 1
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            pass

        return {
            "total_records": total,
            "fallback_rate": fallbacks / total if total > 0 else 0.0,
            "shortcut_rate": shortcuts / total if total > 0 else 0.0,
            "window_seconds": window_seconds
        }
