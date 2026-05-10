from typing import List, Dict, Any
from graph.graph import GraphEngine
from core.logger import get_logger

log = get_logger("cognition.introspection")

class IntrospectionEngine:
    """
    Analyzes the system's own reasoning state for contradictions or uncertainty.
    """
    def __init__(self, graph: GraphEngine):
        self.graph = graph

    def analyze_paths(self, paths: List[Any]) -> Dict[str, Any]:
        """Check for structural weaknesses in a set of reasoning paths."""
        bottlenecks = []
        contradictions = []
        
        for path in paths:
            # Check for low-confidence edges in the path
            for edge_id in path.edge_ids:
                edge = self.graph.get_edge_by_id(edge_id)
                if edge and edge.strength < 0.3:
                    bottlenecks.append({"edge_id": edge_id, "reason": "low_strength"})
                    
        return {
            "bottlenecks": bottlenecks,
            "contradictions": contradictions,
            "overall_coherence": 1.0 - (len(bottlenecks) * 0.1)
        }
