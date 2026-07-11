"""Scoring helpers for the deterministic MCB decision agent."""

from __future__ import annotations

from typing import Iterable, Tuple

from app.services.mcb_models import MCBDecisionInput, ScoreBreakdown, ValidationFlag


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(value: float, scale: float, ceiling: float = 1.0) -> float:
    if scale <= 0:
        return 0.0
    return _clamp(value / scale, 0.0, ceiling)


def _data_completeness(payload: MCBDecisionInput) -> float:
    checks = [
        payload.wholesale.avg_price_pkr is not None,
        payload.wholesale.min_price_pkr is not None,
        payload.wholesale.max_price_pkr is not None,
        payload.wholesale.participant_count > 0,
        payload.retail.avg_price_pkr is not None,
        payload.retail.min_price_pkr is not None,
        payload.retail.max_price_pkr is not None,
        payload.retail.participant_count > 0,
        bool(payload.marketing.segment),
        bool(payload.marketing.positioning),
        bool(payload.marketing.primary_channel),
        bool(getattr(payload.marketing, "quality_band", None)),
        getattr(payload.marketing, "channel_count", 0) >= 1,
    ]
    return round(sum(1 for check in checks if check) / len(checks), 4)


def _market_coverage(payload: MCBDecisionInput) -> float:
    wholesale_coverage = _clamp(payload.wholesale.participant_count / 5.0)
    retail_coverage = _clamp(payload.retail.participant_count / 8.0)
    platform_bonus = 0.15 if payload.retail.participant_count >= 3 else 0.05 if payload.retail.participant_count >= 1 else 0.0
    aggression_penalty = 0.1 if payload.competitors.price_aggression == "high" else 0.0
    return round(_clamp((0.45 * wholesale_coverage) + (0.45 * retail_coverage) + platform_bonus - aggression_penalty), 4)


def _penalty_component(flags: Iterable[ValidationFlag]) -> float:
    penalty = 0.0
    for flag in flags:
        if flag.severity == "critical":
            penalty += 0.22
        elif flag.severity == "warning":
            penalty += 0.07
        else:
            penalty += 0.02
    return round(min(penalty, 0.75), 4)


def _pricing_quality(payload: MCBDecisionInput) -> float:
    analytics = payload.analytics
    retail = payload.retail
    wholesale = payload.wholesale
    sell_price = _as_float(analytics.predicted_price_pkr)
    margin = _as_float(getattr(analytics, "gross_margin_percent", analytics.predicted_margin_percent))
    gross_profit = _as_float(getattr(analytics, "gross_profit_pkr", 0.0))

    margin_score = _clamp(margin / 30.0)
    if margin < 8:
        margin_score = _clamp(margin / 20.0)
    profitability_score = _clamp(max(gross_profit, 0.0) / max(sell_price, 1.0))
    market_fit = 0.65
    if wholesale.avg_price_pkr is not None and sell_price > wholesale.avg_price_pkr:
        market_fit += 0.12
    if retail.min_price_pkr is not None and retail.max_price_pkr is not None and retail.min_price_pkr <= sell_price <= retail.max_price_pkr:
        market_fit += 0.15
    if retail.avg_price_pkr is not None and sell_price > retail.avg_price_pkr * 1.15:
        market_fit -= 0.1
    if margin <= 0:
        return 0.05
    return _clamp((0.45 * margin_score) + (0.25 * profitability_score) + (0.30 * _clamp(market_fit)))


def _demand_score(payload: MCBDecisionInput) -> float:
    retail_participants = payload.retail.participant_count
    pricing_band = 0.0
    if payload.retail.avg_price_pkr:
        spread = 0.0
        if payload.retail.min_price_pkr is not None and payload.retail.max_price_pkr is not None and payload.retail.avg_price_pkr > 0:
            spread = (payload.retail.max_price_pkr - payload.retail.min_price_pkr) / payload.retail.avg_price_pkr
        pricing_band = 1.0 - _clamp(spread)
    return _clamp((retail_participants / 10.0) * 0.55 + pricing_band * 0.25 + _as_float(getattr(payload.analytics, "demand_score", 0.0)) / 100.0 * 0.20)


def _competition_health(payload: MCBDecisionInput) -> float:
    discount_factor = {"low": 0.25, "medium": 0.55, "high": 0.85}.get(payload.competitors.discount_intensity, 0.55)
    aggression_factor = {"low": 0.20, "medium": 0.50, "high": 0.80}.get(payload.competitors.price_aggression, 0.50)
    saturation_factor = _normalize(payload.retail.participant_count, 10.0)
    competition_pressure = _clamp((0.4 * discount_factor) + (0.4 * aggression_factor) + (0.2 * saturation_factor))
    return _clamp(1.0 - competition_pressure)


def _data_quality_score(payload: MCBDecisionInput) -> float:
    analytics = payload.analytics
    signal = _clamp(_as_float(analytics.confidence_score))
    quality_band = str(getattr(analytics, "quality_band", "limited") or "limited")
    band_bonus = {"limited": 0.15, "guarded": 0.35, "balanced": 0.55, "strong": 0.75}.get(quality_band, 0.15)
    completeness = _data_completeness(payload)
    market_coverage = _market_coverage(payload)
    return _clamp((0.45 * signal) + (0.30 * completeness) + (0.25 * market_coverage) + (0.10 * band_bonus))


def _risk_control_score(payload: MCBDecisionInput) -> float:
    analytics = payload.analytics
    market_intelligence_risk = _as_float(getattr(analytics, "risk_score", 0.0)) / 100.0
    gross_profit = _as_float(getattr(analytics, "gross_profit_pkr", 0.0))
    sell_price = max(_as_float(analytics.predicted_price_pkr), 1.0)
    margin_ratio = _clamp(max(gross_profit, 0.0) / sell_price)
    data_penalty = 0.15 if payload.retail.participant_count < 2 else 0.0
    competition_penalty = 0.15 if payload.competitors.price_aggression == "high" else 0.0
    raw_risk = _clamp((0.45 * market_intelligence_risk) + (0.35 * (1.0 - margin_ratio)) + data_penalty + competition_penalty)
    return _clamp(1.0 - raw_risk)


def _marketing_readiness_score(payload: MCBDecisionInput) -> float:
    marketing = payload.marketing
    evidence_coverage = _clamp(_as_float(getattr(marketing, "evidence_coverage_score", 0.0)))
    channel_count = int(getattr(marketing, "channel_count", 0) or 0)
    launch_scope = str(getattr(marketing, "launch_scope", "standard") or "standard")
    quality_band = str(getattr(marketing, "quality_band", "limited") or "limited")
    confidence = _clamp(_as_float(marketing.confidence_score))

    channel_score = _clamp(channel_count / 3.0)
    scope_score = {"narrow": 0.35, "focused": 0.55, "balanced": 0.75, "broad": 0.9}.get(launch_scope, 0.6)
    band_score = {"limited": 0.25, "guarded": 0.5, "balanced": 0.7, "strong": 0.9}.get(quality_band, 0.25)
    return _clamp((0.32 * confidence) + (0.20 * evidence_coverage) + (0.16 * channel_score) + (0.14 * scope_score) + (0.18 * band_score))


def compute_final_confidence(payload: MCBDecisionInput, flags: Iterable[ValidationFlag]) -> Tuple[float, ScoreBreakdown]:
    analytics_component = round(_clamp(payload.analytics.confidence_score) * 0.08, 4)
    marketing_component = round(_clamp(payload.marketing.confidence_score) * 0.08, 4)
    data_completeness_component = round(_data_completeness(payload) * 0.10, 4)
    market_coverage_component = round(_market_coverage(payload) * 0.10, 4)

    pricing_quality = _pricing_quality(payload)
    demand = _demand_score(payload)
    competition = _competition_health(payload)
    data_quality = _data_quality_score(payload)
    risk_control = _risk_control_score(payload)
    marketing_readiness = _marketing_readiness_score(payload)

    pricing_quality_component = round(pricing_quality * 0.20, 4)
    demand_component = round(demand * 0.12, 4)
    competition_component = round(competition * 0.10, 4)
    data_quality_component = round(data_quality * 0.16, 4)
    risk_component = round(risk_control * 0.12, 4)
    marketing_readiness_component = round(marketing_readiness * 0.12, 4)

    penalty_component = _penalty_component(flags)

    final_confidence = _clamp(
        analytics_component
        + marketing_component
        + data_completeness_component
        + market_coverage_component
        + pricing_quality_component
        + demand_component
        + competition_component
        + data_quality_component
        + risk_component
        + marketing_readiness_component
        - penalty_component
    )
    breakdown = ScoreBreakdown(
        analytics_component=analytics_component,
        marketing_component=marketing_component,
        data_completeness_component=data_completeness_component,
        market_coverage_component=market_coverage_component,
        penalty_component=penalty_component,
        pricing_quality_component=pricing_quality_component,
        demand_component=demand_component,
        competition_component=competition_component,
        data_quality_component=data_quality_component,
        risk_component=risk_component,
        marketing_readiness_component=marketing_readiness_component,
    )
    return round(final_confidence, 4), breakdown
