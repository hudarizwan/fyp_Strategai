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


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

import json as _json

MINIMAL_VALID_STRATEGY = {
    "stp": {"segmentation": {}, "targeting": {}, "positioning": {}},
    "swot": {"strengths": ["low cost"], "weaknesses": [], "opportunities": [], "threats": []},
    "pestel": {"political": "stable", "economic": "growing", "social": "online shift",
               "technological": "4G coverage", "environmental": "N/A", "legal": "import duties"},
    "competitor_analysis": {
        "five_forces": {"supplier_power": "medium", "buyer_power": "high",
                        "competitive_rivalry": "high", "threat_of_substitutes": "medium",
                        "threat_of_new_entrants": "low"},
        "key_competitors": ["TechStore"],
        "price_band": {"min": 39000, "max": 40000, "currency": "PKR"},
    },
    "marketing_mix": {
        "product": {"description": "noise cancelling headphones"},
        "price": {"strategy": "competitive", "recommended_sell_pkr": 38000},
        "place": {"channels": ["Daraz"]},
        "promotion": {"tactics": ["social media"]},
    },
    "branding": {"value_proposition": "best sound", "tone": "premium", "tagline": "Hear More"},
    "channels": [{"name": "Daraz", "priority": 1, "rationale": "largest marketplace"}],
    "content_strategy": {"formats": ["video"], "frequency": "3x per week"},
    "launch_plan": {
        "phases": [{"name": "Soft Launch", "duration": "2 weeks", "actions": ["list on Daraz"]}],
        "kpis": [{"metric": "units sold", "target": 50, "period": "month 1"}],
        "measurement_plan": {"tools": ["Daraz analytics"], "cadence": "weekly"},
    },
    "growth_funnel": {
        "model": "AARRR",
        "stages": [{"stage": "Acquisition", "metric": "listing views", "target": 1000}],
    },
    "evidence_ledger": [{"recommendation": "price at 38000", "evidence": ["retail price band 39k-40k"]}],
    "validation_report": {"status": "ok", "checks": [], "flags": []},
    "confidence_score": 0.78,
    "analysis_status": "ok",
}


def test_generate_parses_valid_json_response():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    mock_response = {"message": {"content": _json.dumps(MINIMAL_VALID_STRATEGY)}}
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._generate(enriched)

    assert result["analysis_status"] == "ok"
    assert "stp" in result


def test_generate_extracts_json_from_prose():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    wrapped = f"Here is the strategy:\n```json\n{_json.dumps(MINIMAL_VALID_STRATEGY)}\n```"
    mock_response = {"message": {"content": wrapped}}
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._generate(enriched)

    assert "stp" in result


def test_generate_returns_error_dict_on_unparseable_response():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    mock_response = {"message": {"content": "I cannot generate a strategy."}}
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._generate(enriched)

    assert result["analysis_status"] == "invalid"


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def test_validate_ok_strategy_passes():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    result = agent._validate(MINIMAL_VALID_STRATEGY.copy(), perceived)
    assert result["validation_report"]["status"] == "ok"
    assert result["analysis_status"] == "ok"


def test_validate_missing_key_flags_needs_review():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {k: v for k, v in MINIMAL_VALID_STRATEGY.items() if k != "swot"}
    result = agent._validate(bad, perceived)
    assert result["validation_report"]["status"] == "needs_review"
    assert any("swot" in flag for flag in result["validation_report"]["flags"])


def test_validate_empty_evidence_ledger_flags():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {**MINIMAL_VALID_STRATEGY, "evidence_ledger": []}
    result = agent._validate(bad, perceived)
    assert result["validation_report"]["status"] in ("needs_review", "invalid")
    assert any("evidence_ledger" in flag for flag in result["validation_report"]["flags"])


def test_validate_confidence_out_of_range_flags():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {**MINIMAL_VALID_STRATEGY, "confidence_score": 1.8}
    result = agent._validate(bad, perceived)
    assert any("confidence_score" in flag for flag in result["validation_report"]["flags"])


def test_validate_invalid_analysis_status():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    bad = {**MINIMAL_VALID_STRATEGY, "analysis_status": "invalid"}
    result = agent._validate(bad, perceived)
    assert result["validation_report"]["status"] in ("needs_review", "invalid")


# ---------------------------------------------------------------------------
# Critic + run()
# ---------------------------------------------------------------------------

def test_critic_returns_improved_strategy():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_with_flags = {
        **MINIMAL_VALID_STRATEGY,
        "validation_report": {
            "status": "needs_review",
            "checks": [],
            "flags": ["evidence_ledger:empty"],
        },
        "evidence_ledger": [],
    }
    improved = {**MINIMAL_VALID_STRATEGY, "evidence_ledger": [{"recommendation": "fixed", "evidence": ["price_band"]}]}
    mock_response = {"message": {"content": _json.dumps(improved)}}
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._critic(strategy_with_flags, enriched)
    assert result["evidence_ledger"][0]["recommendation"] == "fixed"


def test_critic_keeps_original_if_parse_fails():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_ok = {**MINIMAL_VALID_STRATEGY}
    mock_response = {"message": {"content": "not json"}}
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = mock_response
        result = agent._critic(strategy_ok, enriched)
    assert result["analysis_status"] == "ok"


def test_run_returns_strategy_with_id():
    agent = _make_agent()
    stored_row = {"id": "xyz-123", **MINIMAL_VALID_STRATEGY,
                  "product_name": "Sony WH-1000XM5", "category": "headsets",
                  "created_at": "2026-04-12T00:00:00Z"}

    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch.object(agent.db, "insert_marketing_strategy", return_value=stored_row):
        mock_ollama.Client.return_value.chat.return_value = {
            "message": {"content": _json.dumps(MINIMAL_VALID_STRATEGY)}
        }
        result = agent.run(
            "Sony WH-1000XM5", "headsets",
            VALID_ANALYTICS, VALID_SCRAPER,
        )
    assert result["id"] == "xyz-123"
