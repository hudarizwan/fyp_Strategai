from __future__ import annotations

from copy import deepcopy
from math import floor
from typing import Any, Dict, List, Sequence

WEIGHTS = {
    'profitability': 0.30,
    'market_opportunity': 0.25,
    'supplier_quality': 0.15,
    'marketing_readiness': 0.15,
    'confidence': 0.15,
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


def _score_signal(value: Any, *, scale: float = 1.0) -> float:
    return _clamp_percent(_as_float(value) * scale)


def _allocate_weighted_breakdown(raw_signals: Dict[str, float]) -> Dict[str, int]:
    weighted = {name: raw_signals[name] * WEIGHTS[name] for name in WEIGHTS}
    target_total = int(round(sum(weighted.values())))
    base = {name: int(floor(value)) for name, value in weighted.items()}
    remainder = target_total - sum(base.values())

    if remainder:
        ranked = sorted(
            weighted.items(),
            key=lambda item: (-(item[1] - floor(item[1])), item[0]),
        )
        for index in range(remainder):
            name = ranked[index % len(ranked)][0]
            base[name] += 1

    return base


def _build_strengths(raw_signals: Dict[str, float]) -> List[str]:
    ordered = [
        ('profitability', raw_signals['profitability'], 'Healthy margin potential'),
        ('market_opportunity', raw_signals['market_opportunity'], 'Strong market opportunity'),
        ('supplier_quality', raw_signals['supplier_quality'], 'Reliable supplier quality'),
        ('marketing_readiness', raw_signals['marketing_readiness'], 'Marketing team is launch-ready'),
        ('confidence', raw_signals['confidence'], 'Analytics confidence is solid'),
    ]
    strengths = [
        label
        for _, score, label in sorted(
            ordered,
            key=lambda item: (-item[1], item[0]),
        )
        if score >= 70.0
    ]
    return strengths[:4] or ['Signals are balanced enough for a cautious launch']


def _build_risks(raw_signals: Dict[str, float]) -> List[str]:
    ordered = [
        ('profitability', raw_signals['profitability'], 'Profitability contribution is modest'),
        ('market_opportunity', raw_signals['market_opportunity'], 'Market opportunity looks limited'),
        ('supplier_quality', raw_signals['supplier_quality'], 'Supplier quality signal is not yet strong'),
        ('marketing_readiness', raw_signals['marketing_readiness'], 'Marketing readiness needs more work'),
        ('confidence', raw_signals['confidence'], 'Analytics confidence is still low'),
    ]
    risks = [
        label
        for _, score, label in sorted(
            ordered,
            key=lambda item: (item[1], item[0]),
        )
        if score < 60.0
    ]
    return risks[:3] or ['No major structural risks are visible']


def _build_executive_summary(overall_score: int, approval_readiness: str, strengths: Sequence[str], risks: Sequence[str]) -> str:
    top_strength = strengths[0] if strengths else 'the current market signals'
    top_risk = risks[0] if risks else 'no material blockers'
    readiness_phrase = {
        'READY': 'is ready for approval',
        'CAUTION': 'is ready with caution',
        'REVIEW': 'needs a human review',
        'DO_NOT_LAUNCH': 'should not launch yet',
    }[approval_readiness]
    return f'Overall score {overall_score} {readiness_phrase}; strongest signal is {top_strength.lower()} while the main watchout is {top_risk.lower()}.'


def _build_next_action(approval_readiness: str, threshold_context: Dict[str, Any]) -> str:
    source_tier = threshold_context.get('threshold_source_tier') or 'hardcoded 0.70'
    if approval_readiness == 'READY':
        return f'Proceed to launch planning using the {source_tier} threshold context.'
    if approval_readiness == 'CAUTION':
        return f'Proceed with a guarded launch and monitor the {source_tier} threshold context.'
    if approval_readiness == 'REVIEW':
        return f'Review the {source_tier} threshold context and tighten weak scoring areas.'
    return f'Pause launch planning and resolve the {source_tier} threshold context gaps first.'


def build_business_decision_summary(
    analytics_result: Dict[str, Any],
    marketing_result: Dict[str, Any],
    threshold_context: Dict[str, Any],
) -> Dict[str, Any]:
    market_intelligence = analytics_result.get('market_intelligence') or {}

    raw_signals = {
        'profitability': _score_signal(analytics_result.get('expected_profit_margin'), scale=100.0 / 40.0),
        'market_opportunity': _score_signal(market_intelligence.get('opportunity_score')),
        'supplier_quality': _score_signal(market_intelligence.get('supplier_quality_score')),
        'marketing_readiness': _score_signal(
            marketing_result.get('marketing_readiness_score', marketing_result.get('marketing_readiness'))
        ),
        'confidence': _score_signal(analytics_result.get('confidence_score'), scale=100.0),
    }

    decision_score_breakdown = _allocate_weighted_breakdown(raw_signals)
    overall_score = int(round(sum(raw_signals[name] * WEIGHTS[name] for name in WEIGHTS)))

    confidence_threshold = _as_float(threshold_context.get('confidence_threshold', 0.70))
    analytics_confidence = _as_float(analytics_result.get('confidence_score'))
    if overall_score >= 85 and analytics_confidence >= confidence_threshold:
        approval_readiness = 'READY'
    elif overall_score >= 70:
        approval_readiness = 'CAUTION'
    elif overall_score >= 55:
        approval_readiness = 'REVIEW'
    else:
        approval_readiness = 'DO_NOT_LAUNCH'

    overall_recommendation = 'Launch' if approval_readiness in {'READY', 'CAUTION'} else 'Hold'
    top_strengths = _build_strengths(raw_signals)
    major_risks = _build_risks(raw_signals)

    return {
        'overall_recommendation': overall_recommendation,
        'overall_score': overall_score,
        'executive_summary': _build_executive_summary(overall_score, approval_readiness, top_strengths, major_risks),
        'top_strengths': top_strengths,
        'major_risks': major_risks,
        'recommended_next_action': _build_next_action(approval_readiness, threshold_context),
        'decision_score_breakdown': decision_score_breakdown,
        'threshold_context': deepcopy(threshold_context),
        'approval_readiness': approval_readiness,
    }
