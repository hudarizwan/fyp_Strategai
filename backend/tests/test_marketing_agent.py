"""Tests for Marketing Agent and ECDB marketing methods."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from app.services.ecdb import ECDB
from app.services.marketing_archetypes import route_strategy_archetype
from app.services.marketing_profile import build_product_profile
from app.services.marketing_prompt_builder import build_compact_analytics_summary, build_competitor_summary
from app.services.marketing_similarity import compare_with_history


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
        import requests
        db.rest_session = requests.Session()
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
    with patch.object(db, "get_latest_marketing_strategy_by_analytics", return_value=None), \
         patch.object(db, "_rest_post", return_value=[fake_row]) as mock_post:
        result = db.insert_marketing_strategy({
            "product_name": "Headphones",
            "category": "headsets",
            "strategy": {"stp": {}},
            "analysis_status": "ok",
            "confidence_score": 0.8,
            "analytics_result_id": "analytics-1",
        })
    assert result["id"] == "aaaa-1111"
    mock_post.assert_called_once_with("marketing_strategies", {
        "product_name": "Headphones",
        "category": "headsets",
        "strategy": {"stp": {}},
        "analysis_status": "ok",
        "strategy_status": "generated",
        "confidence_score": 0.8,
        "analytics_result_id": "analytics-1",
        "version_number": 1,
        "generation_type": "initial",
        "is_latest": True,
    })


def test_insert_marketing_strategy_marks_previous_latest_false():
    db = _make_ecdb_rest()
    previous = {"id": "prev-1", "version_number": 2}
    fake_row = {"id": "new-1", "version_number": 3}
    with patch.object(db, "get_latest_marketing_strategy_by_analytics", return_value=previous), \
         patch.object(db, "_rest_patch", return_value=[] ) as mock_patch, \
         patch.object(db, "_rest_post", return_value=[fake_row]) as mock_post:
        db.insert_marketing_strategy({
            "product_name": "Headphones",
            "category": "headsets",
            "strategy": {"stp": {}},
            "analysis_status": "ok",
            "confidence_score": 0.8,
            "analytics_result_id": "analytics-1",
        })
    mock_patch.assert_called_once_with(
        "marketing_strategies",
        {"is_latest": False},
        {"id": "eq.prev-1"},
    )
    posted = mock_post.call_args.args[1]
    assert posted["version_number"] == 3
    assert posted["generation_type"] == "regenerate"
    assert posted["parent_strategy_id"] == "prev-1"


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


def test_get_latest_marketing_strategy_by_analytics_returns_latest():
    db = _make_ecdb_rest()
    fake_row = {"id": "bbb", "analytics_result_id": "analytics-1", "is_latest": True}
    with patch.object(db, "_rest_get", return_value=[fake_row]) as mock_get:
        result = db.get_latest_marketing_strategy_by_analytics("analytics-1")
    assert result["id"] == "bbb"
    params = mock_get.call_args.args[1]
    assert params["analytics_result_id"] == "eq.analytics-1"
    assert params["is_latest"] == "eq.true"


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
    with _patch("app.services.marketing_agent.ECDB", create=True):
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


def test_perceive_accepts_negative_margin_for_evidence_only_pricing():
    agent = _make_agent()
    bad = {**VALID_ANALYTICS, "expected_profit_margin": -24.3}
    perceived = agent._perceive("Product", "category", bad)

    assert perceived["margin_percent"] == -24.3
    assert perceived["gross_margin_percent"] == -24.3


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
    with _patch("app.services.marketing_agent.ENABLE_MARKETING_CRITIC", True), \
         _patch("app.services.marketing_agent.ollama") as mock_ollama:
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
    with _patch("app.services.marketing_agent.ENABLE_MARKETING_CRITIC", True), \
         _patch("app.services.marketing_agent.ollama") as mock_ollama:
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
    with _patch("app.services.marketing_agent.ENABLE_MARKETING_CRITIC", True), \
         _patch("app.services.marketing_agent.ollama") as mock_ollama:
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response("not json")
        result = agent._critic(strategy_with_flags, enriched)
    assert result["analysis_status"] == "ok"


def test_run_returns_strategy_with_id():
    agent = _make_agent()
    stored_row = {"id": "xyz-123", **MINIMAL_VALID_STRATEGY,
                  "product_name": "Sony WH-1000XM5", "category": "headsets",
                  "created_at": "2026-04-12T00:00:00Z"}

    fake_db = MagicMock()
    fake_db.insert_marketing_strategy.return_value = stored_row
    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch("app.services.ecdb.ECDB", return_value=fake_db):
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(MINIMAL_VALID_STRATEGY)
        )
        result = agent.run(
            "Sony WH-1000XM5", "headsets",
            VALID_ANALYTICS, VALID_SCRAPER,
        )
    assert result["id"] == "xyz-123"
    assert result["storage_status"] == "stored"


def test_run_returns_strategy_even_if_storage_fails():
    agent = _make_agent()
    failing_db = MagicMock()
    failing_db.insert_marketing_strategy.side_effect = RuntimeError("db unavailable")

    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch("app.services.ecdb.ECDB", return_value=failing_db):
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response(
            _json.dumps(MINIMAL_VALID_STRATEGY)
        )
        result = agent.run(
            "Sony WH-1000XM5", "headsets",
            VALID_ANALYTICS, VALID_SCRAPER,
        )

    assert result["analysis_status"] == "ok"
    assert result["storage_status"] == "failed"
    assert "db unavailable" in result["storage_error"]


def test_run_uses_fast_path_for_low_confidence_input():
    agent = _make_agent()
    low_confidence = {
        **VALID_ANALYTICS,
        "confidence_score": 0.2,
        "retail_sellers_count": 0,
    }
    fake_db = MagicMock()
    fake_db.insert_marketing_strategy.return_value = {"id": "fast-1"}

    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch("app.services.ecdb.ECDB", return_value=fake_db):
        result = agent.run(
            "Sony WH-1000XM5", "headsets",
            low_confidence, VALID_SCRAPER,
        )

    mock_ollama.Client.assert_not_called()
    assert result["id"] == "fast-1"
    assert result["analysis_status"] == "ok"
    assert result["validation_report"]["status"] == "ok"


def test_fast_path_differs_for_different_products():
    agent = _make_agent()
    low_confidence = {
        **VALID_ANALYTICS,
        "confidence_score": 0.2,
        "retail_sellers_count": 0,
    }
    audio_perceived = agent._perceive("HyperX Cloud III", "headset", low_confidence)
    audio_enriched = agent._enrich(audio_perceived, VALID_SCRAPER)
    audio_context = agent._build_strategy_context(audio_perceived, audio_enriched, "initial", None)
    audio_strategy = agent._build_fast_path_strategy(audio_enriched, audio_context)

    camera_perceived = agent._perceive("A9 Mini Camera", "camera", low_confidence)
    camera_enriched = agent._enrich(
        camera_perceived,
        {
            "wholesale": {"made_in_china": [{"origin": "China", "moq": 20}]},
            "retail": [{"seller": "SecureCam", "platform": "daraz", "list_price": 2200.0, "detail": {"highlights": "Easy setup camera"}}],
        },
    )
    camera_context = agent._build_strategy_context(camera_perceived, camera_enriched, "initial", None)
    camera_strategy = agent._build_fast_path_strategy(camera_enriched, camera_context)

    assert audio_strategy["pestel"]["social"] != camera_strategy["pestel"]["social"]
    assert audio_strategy["branding"]["tagline"] != camera_strategy["branding"]["tagline"]
    assert audio_strategy["launch_plan"]["phases"][0]["actions"] != camera_strategy["launch_plan"]["phases"][0]["actions"]


def test_regenerate_rotates_strategy_angle():
    agent = _make_agent()
    perceived = agent._perceive("HyperX Cloud III", "headset", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    previous_record = {"strategy": {"strategy_meta": {"strategy_angle": "value_focus"}}}

    fake_db = MagicMock()
    fake_db.get_marketing_strategy_by_id.return_value = previous_record
    agent.db = fake_db

    regenerate_context = agent._build_strategy_context(
        perceived,
        enriched,
        generation_type="regenerate",
        parent_strategy_id="prev-strategy",
    )
    assert regenerate_context["strategy_angle"] != "value_focus"
    assert regenerate_context["variation_type"] == "angle_rotation"


def test_angle_overrides_do_not_clobber_llm_sections():
    agent = _make_agent()
    perceived = agent._perceive("HyperX Cloud III", "headset", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    context = agent._build_strategy_context(perceived, enriched, "regenerate", None)
    strategy = {
        **MINIMAL_VALID_STRATEGY,
        "stp": {
            "segmentation": {"demographics": "Custom demographic", "psychographics": "Custom psychographic"},
            "targeting": {"primary_segment": "Custom segment"},
            "positioning": {"statement": "LLM positioning"},
        },
        "branding": {
            "value_proposition": "Custom value proposition",
            "tone": "bespoke tone",
            "tagline": "LLM tagline",
        },
        "channels": [{"name": "custom_channel", "priority": 1, "rationale": "LLM preferred this route"}],
        "marketing_mix": {
            "product": {"description": "LLM description", "usp": "LLM usp"},
            "price": {"strategy": "LLM price strategy", "recommended_sell_pkr": 38000},
            "place": {"channels": ["custom_channel"]},
            "promotion": {"tactics": ["LLM promotion"]},
        },
    }

    result = agent._apply_strategy_angle_overrides(strategy, enriched, context)

    assert result["stp"]["positioning"]["statement"] == "LLM positioning"
    assert result["branding"]["tagline"] == "LLM tagline"
    assert result["channels"][0]["name"] == "custom_channel"
    assert result["marketing_mix"]["price"]["strategy"] == "LLM price strategy"


def test_product_profile_and_archetype_are_product_specific():
    agent = _make_agent()
    perceived = agent._perceive("HyperX Cloud III", "headset", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    category_profile = agent._infer_category_profile(enriched)
    product_profile = build_product_profile(enriched, category_profile)
    archetype = route_strategy_archetype(product_profile, enriched)

    assert product_profile["product_family"] == "audio"
    assert product_profile["buyer_motivation"] == "performance_and_trust"
    assert archetype["primary"] in {"technical_comparison", "premium_brand"}


def test_compact_summaries_are_small_and_structured():
    agent = _make_agent()
    perceived = agent._perceive("Sony WH-1000XM5", "headsets", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)

    analytics_summary = build_compact_analytics_summary(enriched)
    competitor_summary = build_competitor_summary(enriched)

    assert set(analytics_summary) >= {"buy_price_pkr", "sell_price_pkr", "margin_percent", "platform_count"}
    assert competitor_summary["competitor_names"][0] == "TechStore"
    assert len(competitor_summary["review_themes"]) <= 3


def test_similarity_check_flags_near_duplicate_strategy():
    current = {
        "stp": {"positioning": {"statement": "Clear trust-led headset positioning"}},
        "branding": {"tagline": "Trust-led sound"},
        "channels": [{"name": "daraz", "priority": 1, "rationale": "marketplace first"}],
        "content_strategy": {"formats": ["comparison reels"], "frequency": "3 posts weekly"},
        "launch_plan": {"phases": [{"name": "Launch", "actions": ["run comparison creatives"]}]},
    }
    previous = {
        "id": "prev-1",
        "strategy": {
            "stp": {"positioning": {"statement": "Clear trust-led headset positioning"}},
            "branding": {"tagline": "Trust-led sound"},
            "channels": [{"name": "daraz", "priority": 1, "rationale": "marketplace first"}],
            "content_strategy": {"formats": ["comparison reels"], "frequency": "3 posts weekly"},
            "launch_plan": {"phases": [{"name": "Launch", "actions": ["run comparison creatives"]}]},
        },
    }

    similarity = compare_with_history(current, [previous], threshold=0.5)

    assert similarity["too_similar"] is True
    assert similarity["matched_strategy_id"] == "prev-1"


def test_similarity_guard_regenerates_selected_sections():
    agent = _make_agent()
    perceived = agent._perceive("HyperX Cloud III", "headset", VALID_ANALYTICS)
    enriched = agent._enrich(perceived, VALID_SCRAPER)
    context = agent._build_strategy_context(perceived, enriched, "regenerate", None)
    strategy = {
        **MINIMAL_VALID_STRATEGY,
        "strategy_meta": {},
    }

    previous = {"id": "prev-1", "strategy": strategy}
    patch_strategy = {
        "stp": {"positioning": {"statement": "Different angle positioning"}},
        "branding": {"tagline": "Fresh headline", "tone": "bold"},
        "channels": [{"name": "instagram", "priority": 1, "rationale": "creator-led discovery"}],
        "content_strategy": {"formats": ["creator reels"], "frequency": "daily"},
        "marketing_mix": {"promotion": {"tactics": ["creator seeding"]}},
        "analysis_status": "ok",
    }

    agent._load_previous_strategies = MagicMock(return_value=[previous])
    agent._regenerate_sections = MagicMock(return_value={**strategy, **patch_strategy})

    with _patch("app.services.marketing_agent.ENABLE_SIMILARITY_REGEN", True):
        result = agent._apply_similarity_guard(
            strategy,
            enriched,
            context,
            "HyperX Cloud III",
            "headset",
            "analytics-1",
            None,
        )

    assert result["branding"]["tagline"] == "Fresh headline"
    assert result["strategy_meta"]["similarity_check"]["regenerated_due_to_similarity"] is True


def test_run_falls_back_to_fast_path_when_llm_output_is_invalid():
    agent = _make_agent()
    fake_db = MagicMock()
    fake_db.insert_marketing_strategy.return_value = {"id": "fallback-1"}

    with _patch("app.services.marketing_agent.ollama") as mock_ollama, \
         _patch("app.services.ecdb.ECDB", return_value=fake_db):
        mock_ollama.Client.return_value.chat.return_value = _make_chat_response("not json")
        result = agent.run(
            "Sony WH-1000XM5",
            "headsets",
            VALID_ANALYTICS,
            VALID_SCRAPER,
        )

    assert result["id"] == "fallback-1"
    assert result["analysis_status"] == "ok"
    assert result["validation_report"]["status"] == "ok"
