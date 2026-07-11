"""Tests for Marketing Agent and ECDB marketing methods."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from app.services.ecdb import ECDB
from app.services.marketing_prompt_builder import build_business_state, build_recommendation_cards


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


def _make_chat_response(content: str):
    """Build a mock ChatResponse matching ollama's Pydantic object (attribute access)."""
    response = SimpleNamespace(message=SimpleNamespace(content=content))
    return response


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
    mock_post.assert_called_once_with(
        "marketing_strategies",
        {
            "product_name": "Headphones",
            "category": "headsets",
            "strategy": {"stp": {}},
            "analysis_status": "ok",
            "confidence_score": 0.8,
            "version_number": 1,
            "generation_type": "initial",
            "is_latest": True,
            "strategy_status": "generated",
        },
    )


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

STRUCTURED_ANALYTICS = {
    **VALID_ANALYTICS,
    "primary_pricing_mode": "balanced",
    "alternate_pricing_modes": ["competitive", "premium"],
    "pricing_decision_summary": {
        "selected_mode": "balanced",
        "selection_reason": [
            "Balanced pricing strategy selected",
            "Competition is medium",
            "Demand is high",
        ],
        "supporting_evidence": ["pricing_strategy=balanced", "competition=medium"],
        "confidence_explanation": "Confidence remains high because coverage is stable.",
        "risk_summary": ["No major pricing risk signals after sanity checks."],
        "psychological_adjustment": {
            "applied": False,
            "strategy": "balanced",
            "raw_price_pkr": 38000.0,
            "adjusted_price_pkr": 37999.0,
            "reason": "Rounded to a psychological ending while preserving profitability constraints.",
        },
    },
    "market_intelligence": {
        "competition_score": 74.0,
        "demand_score": 81.0,
        "supplier_quality_score": 68.0,
        "opportunity_score": 77.0,
        "risk_score": 29.0,
    },
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
# Generate — uses attribute-access mock to match real ollama ChatResponse
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




def test_build_business_state_returns_labelled_market_state():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", STRUCTURED_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    business_state = agent._build_business_state(perceived, STRUCTURED_ANALYTICS, enriched)

    assert business_state["market_state"]["pricing_strategy"] == "BALANCED"
    assert business_state["market_state"]["confidence"] == "HIGH"
    assert business_state["market_state"]["competition"] == "HIGH"
    assert business_state["category_playbook"]["positioning"] == "Mid-range Premium"
    assert "Daraz" in business_state["category_playbook"]["primary_channels"]


def test_build_business_state_exposes_richer_category_playbook():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", STRUCTURED_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    business_state = agent._build_business_state(perceived, STRUCTURED_ANALYTICS, enriched)
    playbook = business_state["category_playbook"]

    assert playbook["category_label"] == "Gaming Headsets"
    assert playbook["channel_roles"]["TikTok"] == "discovery"
    assert playbook["audience_profile"]["price_sensitivity"] == "medium"
    assert playbook["typical_margin_band"]["min"] == 30
    assert "Warranty proof" in playbook["promotion_hooks"]


def test_generate_uses_structured_business_state_not_raw_analytics_numbers():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", STRUCTURED_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    business_state = agent._build_business_state(perceived, STRUCTURED_ANALYTICS, enriched)
    generation_input = agent._build_generation_input(perceived, enriched, business_state)

    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(MINIMAL_VALID_STRATEGY)
        )
        agent._generate(generation_input)

    user_content = mock_ollama.Client.return_value.chat.call_args.kwargs["messages"][1]["content"]
    assert '"market_state"' in user_content
    assert '"category_playbook"' in user_content
    assert '"recommended_buy_price_pkr"' not in user_content
    assert '"recommended_sell_price_pkr"' not in user_content


def test_recommendation_cards_reference_evidence_paths_and_confidence():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", STRUCTURED_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    business_state = agent._build_business_state(perceived, STRUCTURED_ANALYTICS, enriched)
    strategy = {
        **MINIMAL_VALID_STRATEGY,
        "marketing_decision_summary": {
            "selected_positioning": "Mid-range Premium",
            "selection_reason": ["Balanced pricing strategy selected"],
            "recommended_channels": ["Daraz", "TikTok"],
            "confidence": "High",
        },
        "channels": [
            {"name": "Daraz", "priority": 1, "rationale": "largest marketplace"},
            {"name": "TikTok", "priority": 2, "rationale": "creator discovery"},
        ],
    }

    cards = build_recommendation_cards(strategy, business_state)

    assert [card["type"] for card in cards] == ["positioning", "channels", "offer", "risk"]
    assert cards[0]["confidence"] == "High"
    assert cards[0]["evidence_refs"] == [
        "marketing_decision_summary.selected_positioning",
        "market_state.pricing_strategy",
    ]
    assert cards[1]["recommendation"] == "Daraz, TikTok"
    assert cards[1]["evidence_refs"] == [
        "marketing_decision_summary.recommended_channels[0]",
        "marketing_decision_summary.recommended_channels[1]",
    ]
    assert cards[2]["evidence_refs"] == [
        "category_playbook.promotion_hooks[0]",
        "category_playbook.buying_factors[0]",
    ]
    assert cards[3]["evidence_refs"] == ["category_playbook.risk_notes[0]"]
    assert all(isinstance(ref, str) and ref for card in cards for ref in card["evidence_refs"])


def test_recommendation_cards_fall_back_to_stp_and_playbook_paths():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", STRUCTURED_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    business_state = agent._build_business_state(perceived, STRUCTURED_ANALYTICS, enriched)
    strategy = {
        **MINIMAL_VALID_STRATEGY,
        "stp": {
            "segmentation": {},
            "targeting": {},
            "positioning": {"statement": "Value-led offer focused on conversion and trust."},
        },
        "marketing_decision_summary": {
            "selection_reason": ["Balanced pricing strategy selected"],
            "confidence": "High",
        },
    }

    cards = build_recommendation_cards(strategy, business_state)

    assert cards[0]["evidence_refs"] == [
        "stp.positioning.statement",
        "market_state.pricing_strategy",
    ]
    assert cards[1]["evidence_refs"] == [
        "category_playbook.primary_channels[0]",
        "category_playbook.primary_channels[1]",
        "category_playbook.primary_channels[2]",
    ]
    assert cards[2]["evidence_refs"] == [
        "category_playbook.promotion_hooks[0]",
        "category_playbook.buying_factors[0]",
    ]
    assert cards[3]["evidence_refs"] == ["category_playbook.risk_notes[0]"]


def test_strategy_consistency_auto_corrects_contradictory_positioning():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", STRUCTURED_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    business_state = agent._build_business_state(perceived, STRUCTURED_ANALYTICS, enriched)
    strategy = {
        **MINIMAL_VALID_STRATEGY,
        "marketing_mix": {
            **MINIMAL_VALID_STRATEGY["marketing_mix"],
            "price": {"strategy": "Premium", "recommended_sell_pkr": 38000},
        },
        "branding": {
            "value_proposition": "Exclusive premium positioning",
            "tone": "Luxury exclusive",
            "tagline": "Own the premium lane",
        },
        "channels": [
            {"name": "Instagram", "priority": 1, "rationale": "luxury brand feel"},
        ],
        "launch_plan": {
            **MINIMAL_VALID_STRATEGY["launch_plan"],
            "phases": [{"name": "Launch", "duration": "2 weeks", "actions": ["go premium"]}],
        },
    }

    corrected = agent._apply_strategy_consistency(strategy, business_state)

    assert corrected["marketing_mix"]["price"]["strategy"] == "Balanced"
    assert "premium" not in corrected["branding"]["tone"].lower()
    assert corrected["marketing_decision_summary"]["selected_positioning"] == "Mid-range Premium"
    assert corrected["marketing_decision_summary"]["confidence"] == "High"


def test_run_includes_marketing_decision_summary():
    agent = _make_agent()
    stored_row = {
        "id": "xyz-123",
        **MINIMAL_VALID_STRATEGY,
        "product_name": "Sony WH-1000XM5",
        "category": "headsets",
        "created_at": "2026-04-12T00:00:00Z",
    }

    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch.object(agent.db, "insert_marketing_strategy", return_value=stored_row):
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(MINIMAL_VALID_STRATEGY)
        )
        result = agent.run(
            "Sony WH-1000XM5",
            "headsets",
            STRUCTURED_ANALYTICS,
            VALID_SCRAPER,
        )

    assert result["id"] == "xyz-123"
    assert result["marketing_decision_summary"]["selected_positioning"] == "Mid-range Premium"
    assert result["marketing_mix"]["price"]["strategy"] == "Balanced"

def test_generate_parses_valid_json_response():
    """Model returns clean JSON — parsed correctly via attribute access."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(MINIMAL_VALID_STRATEGY)
        )
        result = agent._generate(enriched)

    assert result["analysis_status"] == "ok"
    assert "stp" in result


def test_generate_extracts_json_from_fenced_prose():
    """Model wraps JSON in markdown fences — _extract_json recovers it."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    wrapped = f"Here is the strategy:\n```json\n{_json.dumps(MINIMAL_VALID_STRATEGY)}\n```"
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(wrapped)
        result = agent._generate(enriched)

    assert "stp" in result


def test_generate_extracts_json_from_bare_prose():
    """Model adds leading sentence before JSON — rfind approach recovers outermost {}."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    wrapped = f"Sure, here you go:\n{_json.dumps(MINIMAL_VALID_STRATEGY)}\nDone."
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(wrapped)
        result = agent._generate(enriched)

    assert "stp" in result


def test_generate_returns_invalid_on_unparseable_response():
    """Model returns non-JSON text — degraded strategy with analysis_status=invalid."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            "I cannot generate a strategy."
        )
        result = agent._generate(enriched)

    assert result["analysis_status"] == "invalid"


def test_generate_propagates_ollama_connection_error():
    """Ollama connection error propagates — not silently swallowed."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.side_effect = ConnectionError("refused")
        with pytest.raises(ConnectionError):
            agent._generate(enriched)


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
    """Critic is called for hard flags (missing structural keys) and returns improved strategy."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_with_flags = {
        **MINIMAL_VALID_STRATEGY,
        "validation_report": {
            "status": "needs_review",
            "checks": [],
            # Hard flag — missing_key triggers critic (not a soft flag)
            "flags": ["missing_key:channels"],
        },
        "channels": [],
    }
    improved = {**MINIMAL_VALID_STRATEGY, "channels": [{"name": "Daraz", "priority": 1, "rationale": "fixed"}]}
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(improved)
        )
        result = agent._critic(strategy_with_flags, enriched)
    assert result["channels"][0]["name"] == "Daraz"


def test_critic_skips_for_soft_flags_only():
    """Critic is NOT called when all flags are soft (evidence_ledger, kpis) — saves Ollama call."""
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_soft_flags = {
        **MINIMAL_VALID_STRATEGY,
        "validation_report": {
            "status": "needs_review",
            "checks": [],
            "flags": ["evidence_ledger:empty", "launch_plan.kpis:empty"],
        },
        "evidence_ledger": [],
    }
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        result = agent._critic(strategy_soft_flags, enriched)
        # Ollama should NOT be called for soft-only flags
        mock_ollama.Client.assert_not_called()
    # Original strategy returned unchanged
    assert result["analysis_status"] == "ok"


def test_critic_keeps_original_if_parse_fails():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    strategy_with_flags = {
        **MINIMAL_VALID_STRATEGY,
        "validation_report": {"status": "needs_review", "checks": [], "flags": ["some_flag"]},
    }
    with _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response("not json")
        result = agent._critic(strategy_with_flags, enriched)
    assert result["analysis_status"] == "ok"


def test_run_returns_strategy_with_id():
    agent = _make_agent()
    stored_row = {"id": "xyz-123", **MINIMAL_VALID_STRATEGY,
                  "product_name": "Sony WH-1000XM5", "category": "headsets",
                  "created_at": "2026-04-12T00:00:00Z"}

    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch.object(agent.db, "insert_marketing_strategy", return_value=stored_row):
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(MINIMAL_VALID_STRATEGY)
        )
        result = agent.run(
            "Sony WH-1000XM5", "headsets",
            VALID_ANALYTICS, VALID_SCRAPER,
        )
    assert result["id"] == "xyz-123"


