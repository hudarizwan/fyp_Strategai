from app.services.marketing_intelligence import build_marketing_intelligence_bundle


def _strategy_context():
    return {
        "strategy_angle": "value_focus",
        "generation_mode": "llm_hybrid",
        "generation_type": "initial",
        "variation_type": "baseline",
        "category_profile": {
            "family": "audio",
            "price_tier": "mid_market",
            "competition_intensity": "high",
            "audience_archetype": "gaming and entertainment buyers",
            "trust_driver": "authenticity, comfort, and credible feature proof",
            "content_formats": ["demo clips", "comparison reels"],
        },
        "product_profile": {
            "product_family": "audio",
            "purchase_type": "considered_purchase",
            "buyer_motivation": "performance_and_trust",
            "category_behavior": "demo_and_comparison_heavy",
            "trust_sensitivity": "high",
            "comparison_intensity": "high",
            "content_style_needed": "demo-led",
            "price_tier": "mid_market",
            "competition_level": "high",
            "buyer_trigger": "performance_demo",
            "market_maturity": "crowded",
            "supply_flexibility": "strong",
        },
        "strategy_archetype": {"primary": "technical_comparison", "secondary": "trust_and_warranty"},
        "compact_analytics": {"confidence_band": "balanced"},
        "competitor_summary": {"competitor_names": ["TechStore"], "top_platforms": [{"name": "daraz", "count": 5}]},
        "commercial_intelligence": {},
        "quality_band": "balanced",
        "launch_scope": "balanced",
        "evidence_ledger": [{"recommendation": "Use Daraz as anchor", "evidence": ["platform_distribution"]}],
        "previous_strategy_angle": None,
    }


def _enriched():
    return {
        "product_name": "Sony WH-1000XM5",
        "category": "headsets",
        "buy_price_pkr": 28000.0,
        "sell_price_pkr": 38000.0,
        "gross_profit_pkr": 10000.0,
        "gross_margin_percent": 26.3,
        "confidence_score": 0.81,
        "vendor_count": 6,
        "seller_count": 12,
        "low_sample_warning": False,
        "platform_distribution": {"daraz": 5, "instagram": 2},
        "price_band": {"min": 36000.0, "max": 41000.0, "avg": 38000.0},
        "commercial_intelligence": {
            "quality_band": "balanced",
            "profitability_summary": {
                "gross_profit_pkr": 10000.0,
                "gross_margin_percent": 26.3,
                "observed_market_spread_pkr": 10000.0,
                "price_band": {"min": 36000.0, "max": 41000.0, "avg": 38000.0, "currency": "PKR"},
            },
            "market_intelligence": {
                "opportunity_score": 72.0,
                "competition_score": 61.0,
                "supplier_quality_score": 68.0,
                "market_saturation_score": 55.0,
                "data_quality_score": 74.0,
                "risk_score": 33.0,
            },
            "evidence_ledger": [{"recommendation": "Anchor on Daraz", "evidence": ["platform_distribution"]}],
        },
        "market_intelligence": {
            "opportunity_score": 72.0,
            "competition_score": 61.0,
            "supplier_quality_score": 68.0,
            "market_saturation_score": 55.0,
            "data_quality_score": 74.0,
            "risk_score": 33.0,
        },
    }


def test_bundle_builds_consultant_style_modules():
    bundle = build_marketing_intelligence_bundle(_enriched(), _strategy_context())

    assert bundle["customer_intelligence"]["persona"] == "gaming and entertainment buyers"
    assert bundle["channel_recommendation"]["primary_channel"] == "daraz"
    assert len(bundle["channel_recommendation"]["channels"]) <= bundle["channel_recommendation"]["max_channels"]
    assert sum(bundle["budget_recommendation"]["allocation"].values()) == 100
    assert bundle["marketing_validation"]["status"] in {"ok", "needs_review"}
    assert "stp" in bundle["framework_outputs"]
    assert "decision_score_breakdown" in bundle["marketing_decision_summary"]
    assert bundle["marketing_decision_summary"]["approval_readiness"] in {"READY", "CAUTION", "REVIEW", "DO_NOT_LAUNCH"}
