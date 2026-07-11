"""Training entrypoint for the analytics pricing model."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.analytics_agent import AnalyticsAgent


def retrain_analytics_model(limit: int = 300, ecdb_path: Optional[str] = None) -> Dict[str, Any]:
    agent = AnalyticsAgent(ecdb_path=ecdb_path)
    return agent.retrain_from_history(limit=limit)


if __name__ == "__main__":
    result = retrain_analytics_model()
    print(result)
