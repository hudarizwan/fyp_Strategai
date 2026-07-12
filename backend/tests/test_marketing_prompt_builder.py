from app.services.marketing_prompt_builder import build_marketing_system_prompt, build_marketing_user_prompt


def _strategy_context():
    return {
        "product_profile": {
            "product_family": "audio",
            "buyer_trigger": "trust",
            "content_style_needed": "demo-led",
        },
        "strategy_archetype": {"primary": "value_focus", "secondary": "risk_averse"},
        "compact_analytics": {"gross_margin_percent": 22.5, "observed_market_spread_pkr": 1200.0},
        "competitor_summary": {"competitor_count": 3},
        "commercial_intelligence": {},
        "evidence_ledger": [],
        "strategy_angle": "value_focus",
    }


def test_marketing_system_prompt_requests_richer_llm_style():
    prompt = build_marketing_system_prompt(_strategy_context(), "Pakistan context")
    assert "deterministic marketing intelligence bundle" in prompt
    assert "Write a full, rich, LLM-generated go-to-market strategy in the original StrategAI style." in prompt


def test_marketing_user_prompt_requests_detailed_output():
    prompt = build_marketing_user_prompt("Sony Headphones", "headsets", _strategy_context())
    assert "marketing_intelligence" in prompt
    assert "category_playbook" in prompt
    assert "richer, more detailed" in prompt.lower()
    assert "Return JSON only." in prompt


