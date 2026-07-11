from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ecdb import ECDB


MIGRATION_PATH = Path(__file__).resolve().parents[1] / "db" / "migrations" / "004_analytics_outcome_events.sql"


def test_feedback_migration_defines_append_only_outcome_table():
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS analytics_outcome_events" in sql
    assert "feedback_type TEXT NOT NULL" in sql
    assert "actual_buy_price_pkr NUMERIC(12,2)" in sql
    assert "analytics_outcome_events_origin_check" in sql
    assert "feedback_payload JSONB" in sql


def test_insert_analytics_outcome_event_uses_feedback_payload_and_rest_table():
    captured: dict[str, object] = {}

    db = ECDB.__new__(ECDB)
    db.driver_name = "supabase_rest"
    db._new_uuid = lambda: "feedback-id-1"

    def fake_rest_post(table: str, payload):
        captured["table"] = table
        captured["payload"] = payload
        return [payload]

    db._rest_post = fake_rest_post  # type: ignore[assignment]

    result = db.insert_analytics_outcome_event(
        {
            "pipeline_run_id": "run-1",
            "analytics_result_id": "analytics-1",
            "recommendation_id": "rec-1",
            "product_name": "USB C Cable",
            "category": "accessories",
            "feedback_type": "acted_on_recommendation",
            "action_taken": "purchased",
            "actual_buy_price_pkr": 115.0,
            "actual_sell_price_pkr": 240.0,
            "quantity": 50,
            "notes": "Sold in the next promo cycle.",
            "source_page": "results",
        }
    )

    assert captured["table"] == "analytics_outcome_events"
    payload = captured["payload"]
    assert payload["id"] == "feedback-id-1"
    assert payload["feedback_type"] == "acted_on_recommendation"
    assert payload["feedback_payload"]["notes"] == "Sold in the next promo cycle."
    assert result["id"] == "feedback-id-1"
