from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.business_decision_summary import build_business_decision_summary


def test_build_business_decision_summary_uses_documented_weights():
    analytics_result = {
        "expected_profit_margin": 40.0,
        "confidence_score": 0.91,
        "market_intelligence": {
            "opportunity_score": 88.0,
            "supplier_quality_score": 80.0,
        },
    }
    marketing_result = {"marketing_readiness_score": 88}
    threshold_context = {
        "confidence_threshold": 0.70,
        "threshold_source_tier": "exact category",
        "threshold_source_category": "headsets",
    }

    summary = build_business_decision_summary(analytics_result, marketing_result, threshold_context)

    assert summary["overall_score"] == 91
    assert summary["decision_score_breakdown"]["profitability"] == 27
    assert summary["approval_readiness"] == "READY"
    assert summary["overall_recommendation"] == "Launch"
    assert summary["threshold_context"] == threshold_context


def test_build_business_decision_summary_holds_when_score_is_low():
    analytics_result = {
        "expected_profit_margin": 10.0,
        "confidence_score": 0.30,
        "market_intelligence": {
            "opportunity_score": 30.0,
            "supplier_quality_score": 20.0,
        },
    }
    marketing_result = {"marketing_readiness_score": 20}
    threshold_context = {
        "confidence_threshold": 0.70,
        "threshold_source_tier": "hardcoded 0.70",
        "threshold_source_category": None,
    }

    summary = build_business_decision_summary(analytics_result, marketing_result, threshold_context)

    assert summary["overall_score"] < 55
    assert summary["approval_readiness"] == "DO_NOT_LAUNCH"
    assert summary["overall_recommendation"] == "Hold"
