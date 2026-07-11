"""
Enhanced Scraper Agent with real 3-tier fallback handling.
Tier 1: source-specific concurrent scraper service
Tier 2: traditional requests/BeautifulSoup fallback
Tier 3: generic intelligent extraction from fallback HTML
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.agents.base_agent import BDIAgent, Goal, Plan


class EnhancedScraperAgent(BDIAgent):
    """LangGraph-facing scraper agent with data reuse and tiered fallback."""

    def __init__(self, agent_id: str, name: str = "EnhancedScraper"):
        super().__init__(agent_id, name)
        self.tiers = ["platform", "traditional", "generic"]
        self.tier_performance = defaultdict(lambda: {"success": 0, "total": 0})
        self.freshness_hours = 24
        self.min_products = 5

    def generate_goals(self) -> List[Goal]:
        goals = []
        if self.has_belief("product_name") and self.has_belief("category"):
            goals.append(
                Goal(
                    name="scrape_with_fallback",
                    priority=10,
                    params={
                        "product": self.get_belief("product_name"),
                        "category": self.get_belief("category"),
                    },
                )
            )
        return goals

    def create_plan(self, goal: Goal) -> Plan:
        if goal.name == "scrape_with_fallback":
            return Plan(
                steps=[
                    "check_database",
                    "tier1_platform",
                    "tier2_traditional",
                    "tier3_generic",
                    "validate_data",
                ],
                context={
                    "product": goal.params.get("product"),
                    "category": goal.params.get("category"),
                    "skip_scraping": False,
                },
            )
        return Plan(steps=[])

    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        try:
            if action == "check_database":
                fresh_data = self.get_fresh_database_data(context["product"], context["category"])
                if fresh_data:
                    self.update_belief("scraped_data", fresh_data)
                    self.update_belief("data_source", "database")
                    self.update_belief("scraping_success", True)
                    context["skip_scraping"] = True
                    self.log("Using fresh database data")
                return True

            if action == "tier1_platform":
                if context.get("skip_scraping"):
                    return True
                data = self.platform_scrape(context["product"], context["category"])
                if self._store_tier_result("platform", data):
                    context["skip_scraping"] = True
                return True

            if action == "tier2_traditional":
                if context.get("skip_scraping"):
                    return True
                data = self.traditional_scrape(context["product"], context["category"])
                if self._store_tier_result("traditional", data):
                    context["skip_scraping"] = True
                return True

            if action == "tier3_generic":
                if context.get("skip_scraping"):
                    return True
                data = self.generic_extract(context["product"], context["category"])
                self._store_tier_result("generic", data)
                return self.get_belief("scraping_success", False)

            if action == "validate_data":
                success = self.get_belief("scraping_success", False)
                source = self.get_belief("data_source", "unknown")
                self.log(f"Final scraper state: source={source}, success={success}")
                return success

            return False
        except Exception as exc:
            self.log(f"Error in {action}: {exc}")
            return False

    def get_fresh_database_data(self, product_name: str, category: str) -> Optional[Dict[str, Any]]:
        try:
            from app.services.ecdb import ECDB

            db = ECDB()
            wholesale = db.get_wholesale_by_query(product_name, category)
            retail = db.get_retail_by_query(product_name, category)
            if not wholesale and not retail:
                return None

            total_count = len(wholesale) + len(retail)
            if total_count < self.min_products:
                return None

            timestamps = [p.get("scraped_at") for p in (wholesale + retail) if p.get("scraped_at")]
            if not timestamps:
                return None

            latest = max(timestamps)
            if isinstance(latest, str):
                latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))

            if datetime.now() - latest.replace(tzinfo=None) > timedelta(hours=self.freshness_hours):
                return None

            return {
                "wholesale": {"database": wholesale},
                "retail": retail,
                "source": "database",
            }
        except Exception as exc:
            self.log(f"Database check error: {exc}")
            return None

    def platform_scrape(self, product: str, category: str) -> Optional[Dict[str, Any]]:
        from app.services.scraper_service import scrape_product_platforms

        return scrape_product_platforms(product, category, use_parallel=True)

    def traditional_scrape(self, product: str, category: str) -> Optional[Dict[str, Any]]:
        from app.services.scraper_service import scrape_product_platforms_traditional

        return scrape_product_platforms_traditional(product, category)

    def generic_extract(self, product: str, category: str) -> Optional[Dict[str, Any]]:
        from app.services.scraper_service import scrape_product_platforms_generic

        return scrape_product_platforms_generic(product, category)

    def _store_tier_result(self, tier: str, data: Optional[Dict[str, Any]]) -> bool:
        valid = self.validate_scraped_data(data or {})
        self.record_tier_performance(tier, valid)
        if valid:
            self.update_belief("scraped_data", data)
            self.update_belief("data_source", tier)
            self.update_belief("scraping_success", True)
            self.log(f"{tier} tier succeeded")
            return True

        self.log(f"{tier} tier did not produce valid data")
        self.update_belief("scraping_success", False)
        return False

    def validate_scraped_data(self, data: Dict[str, Any]) -> bool:
        if not data:
            return False
        if "wholesale" not in data or "retail" not in data:
            return False

        wholesale = data.get("wholesale", {})
        wholesale_count = sum(len(items) for items in wholesale.values()) if isinstance(wholesale, dict) else len(wholesale)
        retail_count = len(data.get("retail", []))
        return wholesale_count > 0 or retail_count > 0

    def record_tier_performance(self, tier: str, success: bool):
        self.tier_performance[tier]["total"] += 1
        if success:
            self.tier_performance[tier]["success"] += 1

    def get_tier_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for tier, perf in self.tier_performance.items():
            total = perf["total"]
            success = perf["success"]
            stats[tier] = {
                "total": total,
                "success": success,
                "rate": f"{((success / total) * 100) if total else 0:.1f}%",
            }
        return stats

    def export_state(self) -> Dict[str, Any]:
        return {
            "scraped_data": self.get_belief("scraped_data"),
            "data_source": self.get_belief("data_source"),
            "scraping_success": self.get_belief("scraping_success", False),
            "tier_stats": self.get_tier_stats(),
            "current_agent": self.name,
        }
