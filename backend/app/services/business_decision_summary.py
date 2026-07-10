from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Sequence

WEIGHTS = {
    "profitability": 0.30,
    "market_opportunity": 0.25,
    "supplier_quality": 0.15,
    "marketing_readiness": 0.15,
    "confidence": 0.15,
}


def _as_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp_percent(value: float) -> float:
    return max(0.0, min(value, 100.0))


def _weighted_score(raw_score: float, weight: float) -> int:
    return int(round(_clamp_percent(raw_score) * weight))


def _build_strengths(
    profitability: int,
    market_opportunity: int,
    supplier_quality: int,
    marketing_readiness: int,
    confidence: int,
) -> List[str]:
    strengths: List[str] = []
    ordered = [
        (profitability, "Healthy margin potential"),
        (market_opportunity, "Strong market opportunity"),
        (supplier_quality, "Reliable supplier quality"),
        (marketing_readiness, "Marketing team is launch-ready"),
        (confidence, "Analytics confidence is solid"),
    ]
    for score, label in sorted(ordered, key=lambda item: item[0], reverse=True):
        if score >= 20:
            strengths.append(label)
    return strengths[:3] or ["Signals are balanced enough for a cautious launch"]


def _build_risks(
    profitability: int,
    market_opportunity: int,
    supplier_quality: int,
    marketing_readiness: int,
    confidence: int,
    approval_readiness: str,
) -> List[str]:
    risks: List[str] = []
    if profitability < 25:
        risks.append("Profitability contribution is modest")
    if market_opportunity < 25:
        risks.append("Market opportunity looks limited")
    if supplier_quality < 25:
        risks.append("Supplier quality signal is not yet strong")
    if marketing_readiness < 25:
        risks.append("Marketing readiness needs more work")
    if confidence < 25:
        risks.append("Analytics confidence is still low")
    if approval_readiness in {"REVIEW", "DO_NOT_LAUNCH"}:
        risks.append("Overall readiness is below launch threshold")
    return risks[:3] or ["No major structural risks are visible"]


def _build_executive_summary(overall_score: int, approval_readiness: str, strengths: Sequence[str], risks: Sequence[str]) -> str:
    top_strength = strengths[0] if strengths else "the current market signals"
    top_risk = risks[0] if risks else "no material blockers"
    readiness_phrase = {
        "READY": "is ready for approval",
        "CAUTION": "is ready with caution",
        "REVIEW": "needs a human review",
        "DO_NOT_LAUNCH": "should not launch yet",
    }[approval_readiness]
    return f"Overall score {overall_score} {readiness_phrase}; strongest signal is {top_strength.lower()} while the main watchout is {top_risk.lower()}."


def _build_next_action(approval_readiness: str, threshold_context: Dict[str, Any]) -> str:
    source_tier = threshold_context.get("threshold_source_tier") or "hardcoded 0.70"
    if approval_readiness == "READY":
        return f"Proceed to launch planning using the {source_tier} threshold context."
    if approval_readiness == "CAUTION":
        return f"Proceed with a guarded launch and monitor the {source_tier} threshold context."
    if approval_readiness == "REVIEW":
        return f"Review the {source_tier} threshold context and tighten weak scoring areas."
    return f"Pause launch planning and resolve the {source_tier} threshold context gaps first."


def build_business_decision_summary(
    analytics_result: Dict[str, Any],
    marketing_result: Dict[str, Any],
    threshold_context: Dict[str, Any],
) -> Dict[str, Any]:
    market_intelligence = analytics_result.get("market_intelligence") or {}

    profitability_signal = _clamp_percent(_as_float(analytics_result.get("expected_profit_margin")) / 40.0 * 100.0)
    market_opportunity_signal = _clamp_percent(_as_float(market_intelligence.get("opportunity_score")))
    supplier_quality_signal = _clamp_percent(_as_float(market_intelligence.get("supplier_quality_score")))
    marketing_readiness_signal = _clamp_percent(
        _as_float(marketing_result.get("marketing_readiness_score", marketing_result.get("marketing_readiness")))
    )
    confidence_signal = _clamp_percent(_as_float(analytics_result.get("confidence_score")) * 100.0)

    decision_score_breakdown = {
        # The executive card stays conservative on profitability while still surfacing the full signal in the score.
        "profitability": _weighted_score(profitability_signal * 0.9, WEIGHTS["profitability"]),
        "market_opportunity": _weighted_score(market_opportunity_signal, WEIGHTS["market_opportunity"]),
        "supplier_quality": _weighted_score(supplier_quality_signal, WEIGHTS["supplier_quality"]),
        "marketing_readiness": _weighted_score(marketing_readiness_signal, WEIGHTS["marketing_readiness"]),
        "confidence": _weighted_score(confidence_signal, WEIGHTS["confidence"]),
    }
    overall_score = int(
        round(
            (profitability_signal * WEIGHTS["profitability"])
            + (market_opportunity_signal * WEIGHTS["market_opportunity"])
            + (supplier_quality_signal * WEIGHTS["supplier_quality"])
            + (marketing_readiness_signal * WEIGHTS["marketing_readiness"])
            + (confidence_signal * WEIGHTS["confidence"])
        )
    )

    confidence_threshold = _as_float(threshold_context.get("confidence_threshold", 0.70))
    analytics_confidence = _as_float(analytics_result.get("confidence_score"))
    if overall_score >= 85 and analytics_confidence >= confidence_threshold:
        approval_readiness = "READY"
    elif overall_score >= 70:
        approval_readiness = "CAUTION"
    elif overall_score >= 55:
        approval_readiness = "REVIEW"
    else:
        approval_readiness = "DO_NOT_LAUNCH"

    overall_recommendation = "Launch" if approval_readiness in {"READY", "CAUTION"} else "Hold"
    top_strengths = _build_strengths(
        decision_score_breakdown["profitability"],
        decision_score_breakdown["market_opportunity"],
        decision_score_breakdown["supplier_quality"],
        decision_score_breakdown["marketing_readiness"],
        decision_score_breakdown["confidence"],
    )
    major_risks = _build_risks(
        decision_score_breakdown["profitability"],
        decision_score_breakdown["market_opportunity"],
        decision_score_breakdown["supplier_quality"],
        decision_score_breakdown["marketing_readiness"],
        decision_score_breakdown["confidence"],
        approval_readiness,
    )

    return {
        "overall_recommendation": overall_recommendation,
        "overall_score": overall_score,
        "executive_summary": _build_executive_summary(overall_score, approval_readiness, top_strengths, major_risks),
        "top_strengths": top_strengths,
        "major_risks": major_risks,
        "recommended_next_action": _build_next_action(approval_readiness, threshold_context),
        "decision_score_breakdown": decision_score_breakdown,
        "threshold_context": deepcopy(threshold_context),
        "approval_readiness": approval_readiness,
    }
