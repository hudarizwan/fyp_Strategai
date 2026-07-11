from app.services.commercial_intelligence import compute_profitability_snapshot


def test_profitability_snapshot_is_evidence_only():
    snapshot = compute_profitability_snapshot(
        product_name="Demo Product",
        category="headsets",
        buy_price_pkr=100.0,
        sell_price_pkr=160.0,
        confidence_score=0.82,
        low_sample_warning=False,
        wholesale_metrics={"vendor_count": 4, "price_cv": 0.12},
        retail_metrics={"vendor_count": 6, "price_cv": 0.18},
        combined_metrics={"has_both_sources": True},
        price_band={"min": 150.0, "max": 170.0, "avg": 160.0, "currency": "PKR"},
    )

    assert snapshot["cost_profile"] == {}
    assert snapshot["cost_breakdown"] == {}
    assert snapshot["profitability_summary"]["gross_profit_pkr"] == 60.0
    assert snapshot["profitability_summary"]["gross_margin_percent"] == 37.5
    assert snapshot["profitability_summary"]["observed_market_spread_pkr"] == 60.0
    assert "Evidence-based gross margin" in snapshot["profitability_summary"]["profitability_note"]
