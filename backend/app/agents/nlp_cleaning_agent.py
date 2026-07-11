"""
LangGraph/BDI wrapper for the production NLP service.
"""

from typing import Any, Dict, List

from app.agents.base_agent import BDIAgent, Goal, Plan
from app.services.nlp_agent import NLPAgent


class NLPCleaningAgent(BDIAgent):
    """Bridge agent that runs the NLP service pipeline inside agent workflows."""

    def __init__(self, agent_id: str, name: str = "NLP_Cleaner"):
        super().__init__(agent_id, name)
        self.service = None

    def generate_goals(self) -> List[Goal]:
        goals = []
        if self.has_belief("scraped_data") or self.has_belief("raw_scraped_data"):
            goals.append(Goal(name="process_scraped_data", priority=10))
        return goals

    def create_plan(self, goal: Goal) -> Plan:
        if goal.name == "process_scraped_data":
            return Plan(steps=["run_nlp_pipeline", "export_clean_state"])
        return Plan(steps=[])

    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        try:
            if action == "run_nlp_pipeline":
                if self.service is None:
                    self.service = NLPAgent()
                raw_data = self.get_belief("scraped_data") or self.get_belief("raw_scraped_data")
                product_name = self.get_belief("product_name", "")
                category = self.get_belief("category", "")
                result = self.service.process(raw_data, product_name, category, persist=True)

                self.update_belief("nlp_output", result)
                self.update_belief("clean_data", result.get("clean_data"))
                self.update_belief("clustered_products", result.get("clusters", []))
                self.update_belief("records", result.get("records", []))
                self.update_belief("db_saved", bool(result.get("persisted")))
                return True

            if action == "export_clean_state":
                return self.get_belief("clean_data") is not None

            return False
        except Exception as exc:
            self.log(f"Error in {action}: {exc}")
            return False

    def export_state(self) -> Dict[str, Any]:
        return {
            "clean_data": self.get_belief("clean_data"),
            "clustered_products": self.get_belief("clustered_products", []),
            "records": self.get_belief("records", []),
            "db_saved": self.get_belief("db_saved", False),
            "current_agent": self.name,
        }
