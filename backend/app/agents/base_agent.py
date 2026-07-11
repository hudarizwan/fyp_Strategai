"""
Base BDI Agent for LangGraph Integration
Implements Belief-Desire-Intention architecture
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class Belief:
    """Agent's knowledge about the world"""
    key: str
    value: Any
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    
    def is_stale(self, max_age: float = 300) -> bool:
        """Check if belief is outdated"""
        return (time.time() - self.timestamp) > max_age


@dataclass
class Goal:
    """Agent's objective"""
    name: str
    priority: int
    params: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if goal deadline passed"""
        if self.deadline:
            return time.time() > self.deadline
        return False


@dataclass
class Plan:
    """Agent's action plan"""
    steps: List[str]
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_complete(self) -> bool:
        """Check if plan is finished"""
        return self.current_step >= len(self.steps)
    
    def next_action(self) -> Optional[str]:
        """Get next action to execute"""
        if self.is_complete():
            return None
        return self.steps[self.current_step]


class BDIAgent(ABC):
    """
    Base BDI Agent with LangGraph integration
    
    BDI Architecture:
    - Beliefs: What the agent knows
    - Desires: What the agent wants (goals)
    - Intentions: What the agent plans to do
    """
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        
        # BDI components
        self.beliefs: Dict[str, Belief] = {}
        self.goals: List[Goal] = []
        self.current_plan: Optional[Plan] = None
        
        # Performance tracking
        self.actions_taken = 0
        self.successes = 0
        self.failures = 0
    
    # === PERCEPTION (Update Beliefs) ===
    
    def update_belief(self, key: str, value: Any, confidence: float = 1.0):
        """Add or update a belief"""
        self.beliefs[key] = Belief(key, value, confidence)
    
    def get_belief(self, key: str, default: Any = None) -> Optional[Any]:
        """Get belief value if not stale"""
        belief = self.beliefs.get(key)
        if belief and not belief.is_stale():
            return belief.value
        return default
    
    def has_belief(self, key: str) -> bool:
        """Check if belief exists and is not stale"""
        belief = self.beliefs.get(key)
        return belief is not None and not belief.is_stale()
    
    # === DELIBERATION (Generate Goals) ===
    
    @abstractmethod
    def generate_goals(self) -> List[Goal]:
        """
        Generate goals based on current beliefs
        Must be implemented by subclass
        """
        pass
    
    def select_goal(self) -> Optional[Goal]:
        """Select highest priority non-expired goal"""
        # Remove expired goals
        self.goals = [g for g in self.goals if not g.is_expired()]
        
        if not self.goals:
            return None
        
        # Select by priority
        return max(self.goals, key=lambda g: g.priority)
    
    # === PLANNING (Create Plans) ===
    
    @abstractmethod
    def create_plan(self, goal: Goal) -> Plan:
        """
        Create plan to achieve goal
        Must be implemented by subclass
        """
        pass
    
    # === ACTION (Execute Plans) ===
    
    @abstractmethod
    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        """
        Execute single action
        Must be implemented by subclass
        Returns True if successful
        """
        pass
    
    def act(self):
        """Execute current plan step by step"""
        if not self.current_plan:
            return
        
        action = self.current_plan.next_action()
        if not action:
            # Plan complete
            self.current_plan = None
            return
        
        # Execute action
        self.actions_taken += 1
        success = self.execute_action(action, self.current_plan.context)
        
        if success:
            self.successes += 1
            self.current_plan.current_step += 1
        else:
            self.failures += 1
            # Replan on failure
            self.current_plan = None
    
    # === MAIN REASONING CYCLE ===
    
    def run_cycle(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main BDI reasoning cycle
        Compatible with LangGraph
        """
        # 1. PERCEIVE: Update beliefs from state
        for key, value in state.items():
            if value is not None:
                self.update_belief(key, value)
        
        # 2. DELIBERATE: Generate goals
        self.goals = self.generate_goals()
        
        # 3. PLAN: Create plan if needed
        if not self.current_plan and self.goals:
            goal = self.select_goal()
            if goal:
                self.current_plan = self.create_plan(goal)
        
        # 4. ACT: Execute action
        self.act()
        
        # 5. EXPORT: Return updated state
        return self.export_state()
    
    # === LangGraph Integration ===
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph compatible interface
        Allows agent to be used as a node
        """
        return self.run_cycle(state)
    
    @abstractmethod
    def export_state(self) -> Dict[str, Any]:
        """
        Export agent state for LangGraph
        Must be implemented by subclass
        """
        pass
    
    # === UTILITIES ===
    
    def log(self, message: str):
        """Log agent activity"""
        print(f"[{self.name}] {message}")
    
    def get_performance(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        total = self.actions_taken
        success_rate = (self.successes / total * 100) if total > 0 else 0
        
        return {
            'agent_id': self.agent_id,
            'actions_taken': self.actions_taken,
            'successes': self.successes,
            'failures': self.failures,
            'success_rate': success_rate
        }
