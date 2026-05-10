"""cognition/self_monitor.py — Cognitive resource monitoring and load management."""
from __future__ import annotations

import psutil
from typing import Dict, Any, Optional
from graph.graph import GraphEngine
from core.logger import get_logger

log = get_logger("cognition.self_monitor")


class SelfMonitor:
    """
    Monitors system resource usage and cognitive state metrics.
    
    Prevents 'cognitive runaway' by tracking how much of the graph is active
    relative to total capacity and current hardware load.
    """

    def __init__(self, graph: Optional[GraphEngine] = None):
        self.graph = graph
        self.process = psutil.Process()
        self._last_depths: list[int] = []

    def get_health_status(self) -> Dict[str, Any]:
        """Returns hardware and cognitive health metrics."""
        memory_usage_mb = self.process.memory_info().rss / (1024 * 1024)
        cpu_percent = self.process.cpu_percent(interval=None)
        
        # 1. Hardware Load
        load_level = "low"
        if memory_usage_mb > 2048 or cpu_percent > 80:
            load_level = "high"
        elif memory_usage_mb > 1024 or cpu_percent > 50:
            load_level = "medium"

        # 2. Cognitive Saturation
        saturation = 0.0
        if self.graph:
            node_count = self.graph.store.node_count()
            # Simple heuristic: nodes with strength > floor are 'active'
            active_count = len([n for n in self.graph.store.iter_nodes() if n.access_count > 0])
            saturation = active_count / node_count if node_count > 0 else 0.0

        return {
            "memory_mb": round(memory_usage_mb, 2),
            "cpu_percent": cpu_percent,
            "load_level": load_level,
            "cognitive_saturation": round(saturation, 3),
            "status": "healthy" if load_level != "high" and saturation < 0.8 else "throttled"
        }

    def record_reasoning_pass(self, depth: int, nodes_touched: int):
        """Track efficiency of reasoning passes."""
        self._last_depths.append(depth)
        if len(self._last_depths) > 50:
            self._last_depths.pop(0)
            
    def get_recommended_depth_limit(self) -> int:
        """Suggests a max_depth based on current system health."""
        health = self.get_health_status()
        if health["load_level"] == "high":
            return 3
        if health["load_level"] == "medium":
            return 5
        return 10
