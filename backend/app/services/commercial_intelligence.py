from __future__ import annotations

from typing import Any, Dict, List, Optional


QUALITY_BANDS: Dict[str, Dict[str, Any]] = {
    "limited": {
        "max_channels": 2,
        "max_kpis": 3,
        "orders_multiplier": 0.55,
        "views_multiplier": 0.60,
        "content_frequency": "2 focused posts per week",
        "channel_scope": "narrow",
        "launch_scope": "narrow",
    },
    "guarded": {
        "max_channels": 3,
        "max_kpis": 4,
        "orders_multiplier": 0.75,
        "views_multiplier": 0.80,
        "content_frequency": "3 focused posts per week",
        "channel_scope": "focused",
        "launch_scope": "focused",
    },
    "balanced": {
        "max_channels": 4,
        "max_kpis": 4,
        "orders_multiplier": 0.95,
        "views_multiplier": 0.95,
        "content_frequency": "3 focused posts per week",
        "channel_scope": "balanced",
        "launch_scope": "balanced",
    },
    "strong": {
        "max_channels": 4,
        "max_kpis": 5,
        "orders_multiplier": 1.10,
        "views_multiplier": 1.10,
        "content_frequency": "4 focused posts per week",
        "channel_scope": "broad",
        "launch_scope": "broad",
    },
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def infer_market_family(product_name: str = "", category: str = "") -> str:
    combined = f"{product_name} {category}".lower()
    if any(token in combined for token in ("iphone", "samsung", "redmi", "infinix", "mobile", "phone")):
        return "mobile_phones"
    if any(token in combined for token in ("laptop", "macbook", "notebook", "chromebook", "thinkpad")):
        return "laptops"
    if any(token in combined for token in ("headset", "headphone", "earbud", "earphone", "audio", "speaker")):
        return "headsets"
    if any(token in combined for token in ("camera", "cctv", "webcam", "surveillance")):
        return "cameras"
    if any(token in combined for token in ("charger", "cable", "adapter", "power bank", "case", "cover")):
        return "mobile_accessories"
    if any(token in combined for token in ("mouse", "keyboard", "ssd", "router", "monitor", "accessor")):
        return "computer_accessories"
    if any(token in combined for token in ("makeup", "cream", "serum", "beauty", "skincare")):
        return "beauty"
    if any(token in combined for token in ("shirt", "dress", "shoe", "bag", "fashion")):
        return "fashion"
    if any(token in combined for token in ("home", "kitchen", "furniture", "organizer", "pillow")):
        return "home_goods"
    if "retail" in combined or "general" in combined:
        return "general_retail"
    return "generic_gadgets"


def classify_quality_band(
    confidence_score: float,
    low_sample_warning: bool,
    wholesale_vendor_count: int,
    retail_listing_count: int,
    margin_percent: Optional[float] = None,
) -> str:
    confidence = _safe_float(confidence_score)
    if low_sample_warning or wholesale_vendor_count < 3 or retail_listing_count < 5:
        return "limited"
    if confidence < 0.55 or (margin_percent is not None and margin_percent < 8.0):
        return "guarded"
    if confidence < 0.75 or (margin_percent is not None and margin_percent < 15.0):
        return "balanced"
    return "strong"


def compute_profitability_snapshot(
    *,
    product_name: str,
    category: str,
    buy_price_pkr: float,
    sell_price_pkr: float,
    confidence_score: float,
    low_sample_warning: bool,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    price_band: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    buy = max(_safe_float(buy_price_pkr), 0.0)
    sell = max(_safe_float(sell_price_pkr), 0.0)
    price_band = price_band or {}

    gross_profit = round(sell - buy, 2)
    gross_margin_percent = round((gross_profit / sell) * 100.0, 2) if sell > 0 else 0.0
    observed_market_spread = gross_profit

    price_cv = max(_safe_float(retail_metrics.get("price_cv", 0.0)), _safe_float(wholesale_metrics.get("price_cv", 0.0)))
    profitability_confidence = _clamp(
        _safe_float(confidence_score)
        - (0.08 if low_sample_warning else 0.0)
        - min(price_cv * 0.10, 0.15)
        - (0.04 if gross_margin_percent < 10 else 0.0)
    )

    risk_notes: List[str] = []
    if low_sample_warning:
        risk_notes.append("limited data sample raises forecast uncertainty")
    if gross_margin_percent < 10:
        risk_notes.append("gross margin is thin after market comparison")
    if _safe_float(retail_metrics.get("price_cv", 0.0)) > 0.35:
        risk_notes.append("retail pricing variance is high")
    if _safe_float(wholesale_metrics.get("price_cv", 0.0)) > 0.35:
        risk_notes.append("wholesale pricing variance is high")
    if not risk_notes:
        risk_notes.append("price spread remains commercially manageable")

    quality_band = classify_quality_band(
        confidence_score=confidence_score,
        low_sample_warning=low_sample_warning,
        wholesale_vendor_count=_safe_int(wholesale_metrics.get("vendor_count", 0)),
        retail_listing_count=_safe_int(retail_metrics.get("vendor_count", 0)),
        margin_percent=gross_margin_percent,
    )

    return {
        "product_name": product_name,
        "category": category,
        "buy_price_pkr": round(buy, 2),
        "sell_price_pkr": round(sell, 2),
        "quality_band": quality_band,
        "cost_profile": {},
        "cost_breakdown": {},
        "profitability_summary": {
            "gross_profit_pkr": gross_profit,
            "gross_margin_percent": gross_margin_percent,
            "observed_market_spread_pkr": observed_market_spread,
            "profitability_confidence": round(profitability_confidence, 4),
            "risk_notes": risk_notes,
            "price_band": {
                "min": round(_safe_float(price_band.get("min", 0.0)), 2),
                "max": round(_safe_float(price_band.get("max", 0.0)), 2),
                "avg": round(_safe_float(price_band.get("avg", 0.0)), 2),
                "currency": price_band.get("currency", "PKR"),
            },
            "profitability_note": "Evidence-based gross margin derived from the observed buy/sell spread.",
        },
    }


def build_market_intelligence_snapshot(
    *,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    profitability_snapshot: Dict[str, Any],
    confidence_score: float,
    low_sample_warning: bool,
) -> Dict[str, Any]:
    wholesale_count = _safe_int(wholesale_metrics.get("vendor_count", 0))
    retail_count = _safe_int(retail_metrics.get("vendor_count", 0))
    wholesale_cv = _safe_float(wholesale_metrics.get("price_cv", 0.0))
    retail_cv = _safe_float(retail_metrics.get("price_cv", 0.0))
    retail_price_band = profitability_snapshot.get("profitability_summary", {}).get("price_band", {}) or {}
    gross_margin = _safe_float(profitability_snapshot.get("profitability_summary", {}).get("gross_margin_percent", 0.0))
    gross_profit = _safe_float(profitability_snapshot.get("profitability_summary", {}).get("gross_profit_pkr", 0.0))
    profitability_confidence = _safe_float(profitability_snapshot.get("profitability_summary", {}).get("profitability_confidence", confidence_score))

    demand_score = _clamp(
        (retail_count / 10.0) * 0.45
        + (1.0 - min(retail_cv, 1.0)) * 0.25
        + (1.0 if combined_metrics.get("has_both_sources") else 0.5) * 0.20
        + _safe_float(confidence_score) * 0.10
    ) * 100.0
    competition_pressure = _clamp(
        (retail_count / 12.0) * 0.40
        + min(retail_cv, 1.0) * 0.25
        + (0.20 if combined_metrics.get("has_both_sources") else 0.10)
        + (0.15 if low_sample_warning else 0.0)
    ) * 100.0
    supplier_quality = _clamp(
        (wholesale_count / 8.0) * 0.45
        + (1.0 - min(wholesale_cv, 1.0)) * 0.35
        + (0.20 if combined_metrics.get("has_both_sources") else 0.0)
    ) * 100.0
    market_saturation = _clamp(
        (retail_count / 14.0) * 0.55
        + min(retail_cv, 1.0) * 0.30
        + (0.15 if not combined_metrics.get("has_both_sources") else 0.0)
    ) * 100.0
    data_quality = _clamp(
        _safe_float(confidence_score) * 0.45
        + (0.25 if not low_sample_warning else 0.10)
        + (0.15 if wholesale_count >= 3 else 0.05)
        + (0.15 if retail_count >= 5 else 0.05)
    ) * 100.0
    risk_score = _clamp(
        (100.0 - max(gross_margin, 0.0) * 0.85) / 100.0
        + (0.20 if low_sample_warning else 0.0)
        + min(retail_cv * 0.25, 0.20)
        + (0.15 if market_saturation > 60 else 0.0)
    ) * 100.0
    opportunity_score = _clamp(
        (demand_score / 100.0) * 0.40
        + (supplier_quality / 100.0) * 0.15
        + max(gross_margin, 0.0) / 100.0 * 0.30
        + (1.0 - risk_score / 100.0) * 0.15
    ) * 100.0

    confidence_band = classify_quality_band(
        confidence_score=confidence_score,
        low_sample_warning=low_sample_warning,
        wholesale_vendor_count=wholesale_count,
        retail_listing_count=retail_count,
        margin_percent=gross_margin,
    )

    return {
        "confidence_band": confidence_band,
        "confidence_score": round(profitability_confidence * 100.0, 2),
        "demand_score": round(demand_score, 2),
        "competition_score": round(competition_pressure, 2),
        "supplier_quality_score": round(supplier_quality, 2),
        "market_saturation_score": round(market_saturation, 2),
        "data_quality_score": round(data_quality, 2),
        "risk_score": round(risk_score, 2),
        "opportunity_score": round(opportunity_score, 2),
        "reasoning": {
            "demand": [
                f"{retail_count} retail seller signal(s) support visible market interest." if retail_count else "No retail seller evidence is present yet.",
                f"Retail band remains at PKR {retail_price_band.get('min', 0):,.0f}-{retail_price_band.get('max', 0):,.0f}." if retail_price_band else "Retail band is still incomplete.",
            ],
            "competition": [
                f"Retail price variance is {retail_cv:.2f}, which indicates {('strong' if retail_cv > 0.35 else 'moderate' if retail_cv > 0.18 else 'tight')} pricing pressure.",
                "Low sample size keeps competition estimates conservative." if low_sample_warning else "Sample size is broad enough for a more stable competition read.",
            ],
            "supplier": [
                f"{wholesale_count} wholesale supplier signal(s) are available for sourcing review.",
                f"Wholesale variance is {wholesale_cv:.2f}, which suggests {('active negotiation room' if wholesale_cv < 0.18 else 'some price spread' if wholesale_cv < 0.35 else 'volatile supplier pricing')}.",
            ],
            "risk": [
                f"Gross margin sits at {gross_margin:.2f}% based on the observed buy/sell spread.",
                "Risk is elevated because the market sample is limited." if low_sample_warning else "Risk stays more manageable because the sample is reasonably broad.",
            ],
            "opportunity": [
                f"Gross profit leaves PKR {gross_profit:.2f} of observed spread and {gross_margin:.2f}% gross margin.",
                f"The observed buy/sell spread is PKR {profitability_snapshot.get('profitability_summary', {}).get('observed_market_spread_pkr', 0):,.0f}.",
            ],
        },
    }


def build_evidence_ledger(
    *,
    product_name: str,
    category: str,
    wholesale_metrics: Dict[str, Any],
    retail_metrics: Dict[str, Any],
    combined_metrics: Dict[str, Any],
    profitability_snapshot: Dict[str, Any],
    market_intelligence: Dict[str, Any],
    price_band: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    price_band = price_band or {}
    ledger: List[Dict[str, Any]] = []
    gross = profitability_snapshot.get("profitability_summary", {})

    ledger.append(
        {
            "section": "pricing",
            "recommendation": (
                f"Use a gross profit target around PKR {gross.get('gross_profit_pkr', 0):,.0f} "
                f"with a gross margin of {gross.get('gross_margin_percent', 0):.1f}%."
            ),
            "evidence": [
                f"recommended_buy_price_pkr={profitability_snapshot.get('buy_price_pkr', 0)}",
                f"recommended_sell_price_pkr={profitability_snapshot.get('sell_price_pkr', 0)}",
                f"gross_profit_pkr={gross.get('gross_profit_pkr', 0)}",
                f"gross_margin_percent={gross.get('gross_margin_percent', 0)}",
                f"observed_market_spread_pkr={gross.get('observed_market_spread_pkr', 0)}",
            ],
        }
    )
    ledger.append(
        {
            "section": "demand",
            "recommendation": (
                f"Treat demand as {market_intelligence.get('confidence_band', 'balanced')} because retail coverage is "
                f"{_safe_int(retail_metrics.get('vendor_count', 0))} listings and the observed band is PKR "
                f"{price_band.get('min', 0):,.0f}-{price_band.get('max', 0):,.0f}."
            ),
            "evidence": [
                f"retail_sellers_count={retail_metrics.get('vendor_count', 0)}",
                f"retail_price_cv={retail_metrics.get('price_cv', 0)}",
                f"market_saturation_score={market_intelligence.get('market_saturation_score', 0)}",
            ],
        }
    )
    ledger.append(
        {
            "section": "competition",
            "recommendation": (
                f"Pricing pressure is {market_intelligence.get('competition_score', 0):.0f}/100, so the strategy should "
                f"stay aligned to the observed retail band and not rely on aggressive widening."
            ),
            "evidence": [
                f"retail_sellers_count={retail_metrics.get('vendor_count', 0)}",
                f"retail_price_band_min={price_band.get('min', 0)}",
                f"retail_price_band_max={price_band.get('max', 0)}",
                f"retail_price_cv={retail_metrics.get('price_cv', 0)}",
            ],
        }
    )
    ledger.append(
        {
            "section": "supplier",
            "recommendation": (
                f"Supplier quality is {market_intelligence.get('supplier_quality_score', 0):.0f}/100, so sourcing should "
                f"prefer the strongest vendors while preserving MOQ discipline."
            ),
            "evidence": [
                f"wholesale_vendors_count={wholesale_metrics.get('vendor_count', 0)}",
                f"wholesale_price_cv={wholesale_metrics.get('price_cv', 0)}",
                f"moq_min={combined_metrics.get('moq_min', 'n/a')}",
            ],
        }
    )
    ledger.append(
        {
            "section": "risk",
            "recommendation": (
                f"Risk is {market_intelligence.get('risk_score', 0):.0f}/100 because the price spread and sample size "
                f"need to be treated carefully."
            ),
            "evidence": [
                f"gross_margin_percent={gross.get('gross_margin_percent', 0)}",
                f"profitability_confidence={gross.get('profitability_confidence', 0)}",
                f"quality_band={profitability_snapshot.get('quality_band', 'balanced')}",
            ],
        }
    )

    if combined_metrics.get("has_both_sources"):
        ledger.append(
            {
                "section": "validation",
                "recommendation": "Use both wholesale and retail evidence because the comparison is grounded on both sides of the market.",
                "evidence": [
                    "has_both_sources=True",
                    f"platform_count={combined_metrics.get('platform_count', 0)}",
                    f"vendor_count={combined_metrics.get('vendor_count', 0)}",
                ],
            }
        )
    return ledger
