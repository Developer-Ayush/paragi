"""cognition/goal_manager.py — Hierarchical goal decomposition and pursuit tracking."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from graph.graph import GraphEngine
from core.enums import EdgeType


@dataclass
class Goal:
    id: str
    description: str
    status: str = "active"  # active | satisfied | blocked
    subgoals: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    priority: float = 1.0


class GoalManager:
    """
    Manages the system's long-term and short-term reasoning objectives.
    
    Architectural Role:
    The intentionality layer. It decomposes top-level user requests into 
    executable graph reasoning tasks and tracks their satisfaction.
    """

    def __init__(self, graph: Optional[GraphEngine] = None):
        self.graph = graph
        self.goals: Dict[str, Goal] = {}

    def create_goal(self, description: str, parent_id: Optional[str] = None) -> Goal:
        """Create a new goal and optionally decompose it."""
        gid = uuid.uuid4().hex[:8]
        goal = Goal(id=gid, description=description, parent_id=parent_id)
        self.goals[gid] = goal
        
        if parent_id and parent_id in self.goals:
            self.goals[parent_id].subgoals.append(gid)
            
        # If we have a graph, attempt automatic decomposition via DEPENDS_ON edges
        if self.graph:
            self._decompose_goal(goal)
            
        return goal

    def _decompose_goal(self, goal: Goal):
        """Recursively finds dependencies in the graph to create subgoals."""
        node = self.graph.get_node_by_label(goal.description)
        if not node:
            return

        # Find what this goal DEPENDS_ON
        neighbors = self.graph.get_neighbors(goal.description)
        deps = [n for n in neighbors if n.type == EdgeType.DEPENDS_ON]
        
        for edge in deps:
            dep_label = self.graph.get_node_label(edge.target)
            # Avoid infinite recursion
            if any(g.description == dep_label for g in self.goals.values()):
                continue
            self.create_goal(description=dep_label, parent_id=goal.id)

    def update_goal_status(self, goal_id: str, status: str):
        if goal_id in self.goals:
            self.goals[goal_id].status = status
            
    def get_active_leaf_goals(self) -> List[Goal]:
        """Returns active goals that have no subgoals (executable tasks)."""
        return [g for g in self.goals.values() if g.status == "active" and not g.subgoals]

    def to_dict(self) -> List[Dict]:
        return [
            {
                "id": g.id,
                "description": g.description,
                "status": g.status,
                "subgoals": g.subgoals,
                "parent_id": g.parent_id
            }
            for g in self.goals.values()
        ]
