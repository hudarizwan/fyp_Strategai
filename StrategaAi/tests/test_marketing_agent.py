"""Tests for Marketing Agent and ECDB marketing methods."""
import json
from unittest.mock import MagicMock, patch
import pytest

from app.services.ecdb import ECDB


def _make_ecdb_rest():
    """Return an ECDB wired to REST-only mode (no live DB needed)."""
    with patch("app.services.ecdb.SUPABASE_DB_URL", ""), \
         patch("app.services.ecdb.SUPABASE_URL", "http://fake.supabase"), \
         patch("app.services.ecdb.SUPABASE_KEY", "fake-key"), \
         patch("app.services.ecdb.SUPABASE_SERVICE_KEY", "fake-service-key"), \
         patch.object(ECDB, "_connect", return_value=None), \
         patch.object(ECDB, "_init_database", return_value=None):
        db = ECDB.__new__(ECDB)
        db.driver_name = "supabase_rest"
        db.rest_base_url = "http://fake.supabase"
        db.rest_headers = {"apikey": "fake-key", "Authorization": "Bearer fake-key"}
        return db


def test_insert_marketing_strategy_returns_row():
    db = _make_ecdb_rest()
    fake_row = {
        "id": "aaaa-1111",
        "product_name": "Headphones",
        "category": "headsets",
        "analysis_status": "ok",
        "confidence_score": 0.8,
        "created_at": "2026-04-12T00:00:00Z",
    }
    with patch.object(db, "_rest_post", return_value=[fake_row]) as mock_post:
        result = db.insert_marketing_strategy({
            "product_name": "Headphones",
            "category": "headsets",
            "strategy": {"stp": {}},
            "analysis_status": "ok",
            "confidence_score": 0.8,
        })
    assert result["id"] == "aaaa-1111"
    mock_post.assert_called_once_with("marketing_strategies", {
        "product_name": "Headphones",
        "category": "headsets",
        "strategy": {"stp": {}},
        "analysis_status": "ok",
        "confidence_score": 0.8,
    })


def test_get_marketing_history_returns_list():
    db = _make_ecdb_rest()
    fake_rows = [
        {"id": "aaa", "product_name": "Headphones", "analysis_status": "ok",
         "confidence_score": 0.8, "created_at": "2026-04-12T00:00:00Z"},
    ]
    with patch.object(db, "_rest_get", return_value=fake_rows):
        result = db.get_marketing_history(limit=5)
    assert len(result) == 1
    assert result[0]["id"] == "aaa"


def test_get_marketing_strategy_by_id_returns_row():
    db = _make_ecdb_rest()
    fake_row = {"id": "bbb", "product_name": "Mouse", "strategy": {"stp": {}}}
    with patch.object(db, "_rest_get", return_value=[fake_row]):
        result = db.get_marketing_strategy_by_id("bbb")
    assert result["id"] == "bbb"


def test_get_marketing_strategy_by_id_not_found():
    db = _make_ecdb_rest()
    with patch.object(db, "_rest_get", return_value=[]):
        result = db.get_marketing_strategy_by_id("missing-id")
    assert result is None


# ---------------------------------------------------------------------------
# Perceive + Enrich
# ---------------------------------------------------------------------------

from unittest.mock import patch as _patch

VALID_ANALYTICS = {
    "recommended_buy_price_pkr": 28000.0,
    "recommended_sell_price_pkr": 38000.0,
    "expected_profit_margin": 26.3,
    "confidence_score": 0.81,
    "confidence_reason": "sufficient data",
    "wholesale_vendors_count": 6,
    "retail_sellers_count": 12,
}

VALID_SCRAPER = {
    "wholesale": {
        "made_in_china": [
            {"supplier": "Shenzhen Co", "unit_price": 100.0, "unit_price_pkr": 28000.0,
             "currency": "USD", "moq": 10, "origin": "China"},
        ]
    },
    "retail": [
        {"seller": "TechStore", "platform": "daraz", "list_price": 39000.0,
         "title": "Sony WH-1000XM5", "url": "https://daraz.pk/1",
         "detail": {"highlights": "Great noise cancelling, fast delivery"}},
        {"seller": "GadgetHub", "platform": "daraz", "list_price": 40000.0,
         "title": "Sony Headphones", "url": "https://daraz.pk/2", "detail": {}},
    ],
}


def _make_agent():
    with _patch("app.services.marketing_agent.ECDB"):
        from app.services.marketing_agent import MarketingAgent
        agent = MarketingAgent(ollama_base_url="http://localhost:11434", model="llama3.1:8b")
    return agent


def test_perceive_valid_input():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    assert perceived["product_name"] == "Sony WH-1000XM5"
    assert perceived["buy_price_pkr"] == 28000.0
    assert perceived["sell_price_pkr"] == 38000.0
    assert perceived["margin_percent"] == 26.3
    assert perceived["confidence_score"] == 0.81
    assert perceived["vendor_count"] == 6
    assert perceived["seller_count"] == 12


def test_perceive_missing_required_field_raises():
    agent = _make_agent()
    bad = {k: v for k, v in VALID_ANALYTICS.items() if k != "recommended_buy_price_pkr"}
    with pytest.raises(ValueError, match="recommended_buy_price_pkr"):
        agent._perceive("Product", "category", bad)


def test_perceive_negative_price_raises():
    agent = _make_agent()
    bad = {**VALID_ANALYTICS, "recommended_buy_price_pkr": -100.0}
    with pytest.raises(ValueError, match="positive"):
        agent._perceive("Product", "category", bad)


def test_perceive_confidence_out_of_range_raises():
    agent = _make_agent()
    bad = {**VALID_ANALYTICS, "confidence_score": 1.5}
    with pytest.raises(ValueError, match="confidence_score"):
        agent._perceive("Product", "category", bad)


def test_enrich_extracts_competitors():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    assert enriched["competitor_count"] == 2
    assert enriched["price_band"]["min"] == 39000.0
    assert enriched["price_band"]["max"] == 40000.0
    assert "TechStore" in enriched["competitor_names"]


def test_enrich_extracts_wholesale_origins():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    assert "China" in enriched["wholesale_origins"]
    assert enriched["moq_range"]["min"] == 10


def test_enrich_extracts_review_themes():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    assert len(enriched["review_themes"]) > 0
